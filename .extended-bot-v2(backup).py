
import asyncio
import os
import uuid
import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional

from dotenv import load_dotenv

from x10.perpetual.configuration import STARKNET_MAINNET_CONFIG
from x10.perpetual.trading_client.trading_client import PerpetualTradingClient
from x10.perpetual.accounts import StarkPerpetualAccount
from x10.perpetual.orders import OrderSide, TimeInForce
from x10.perpetual.positions import PositionSide

from config import MARKETS, BUY_QTY, PRICE_PRECISION, SIZE_PRECISION, TICK_SECONDS
from config import BUY_TTL_SECONDS, BUY6_STEP_PCT, SELL_STEPS_PCT, SELL_SPLIT, PNL_MIN_PCT, BRANCH_SL_PCT

load_dotenv()

API_KEY = os.getenv("EXTENDED_API_KEY")
STARK_PUBLIC_KEY = os.getenv("EXTENDED_PUBLIC_KEY")
STARK_PRIVATE_KEY = os.getenv("EXTENDED_STARK_PRIVATE")
VAULT_ID = int(os.getenv("EXTENDED_VAULT_ID")) if os.getenv("EXTENDED_VAULT_ID") else None

STATE_FILE = os.getenv("BOT_STATE_FILE", "bot_state.json")

def rprice(symbol: str, v: Decimal) -> Decimal:
    p = PRICE_PRECISION.get(symbol, 2)
    q = Decimal(10) ** (-p)
    return (v.quantize(q))

def rsize(symbol: str, v: Decimal) -> Decimal:
    # Для BTC используем точность 4 знака после запятой
    if symbol == "BTC-USD":
        p = 4
    else:
        p = SIZE_PRECISION.get(symbol, 6)
    
    q = Decimal(10) ** (-p)
    vq = v.quantize(q)
    if vq == 0 and v > 0:
        return q
    
    # Убеждаемся, что размер соответствует требованиям API
    min_size = Decimal("0.0001")  # Минимальный размер для BTC
    
    # Для BTC разрешаем промежуточные значения: 0.0001, 0.0002, 0.0003, 0.0004
    if symbol == "BTC-USD":
        # Округляем до ближайшего допустимого значения
        if vq < min_size:
            return min_size
        elif vq < Decimal("0.0002"):
            return Decimal("0.0001")
        elif vq < Decimal("0.0003"):
            return Decimal("0.0002")
        elif vq < Decimal("0.0004"):
            return Decimal("0.0003")
        else:
            return Decimal("0.0004")
    
    # Для других символов используем стандартную логику
    if vq < min_size:
        return min_size
    return vq

@dataclass
class SellLeg:
    leg: str
    target_pct: Decimal
    size: Decimal
    order_id: Optional[int] = None
    client_id: Optional[str] = None
    price: Optional[Decimal] = None

@dataclass
class Branch:
    branch_id: int
    symbol: str
    buy_price: Decimal
    size: Decimal
    wap: Decimal
    stop_price: Decimal
    active: bool = True
    sells: Dict[str, SellLeg] = field(default_factory=dict)

class Bot:
    def __init__(self, client: PerpetualTradingClient):
        self.c = client
        self.branches: Dict[str, Dict[int, Branch]] = {m: {} for m in MARKETS}
        self.next_branch_id: Dict[str, int] = {m: 1 for m in MARKETS}
        self.buy1_done: Dict[str, bool] = {m: False for m in MARKETS}
        self.buy1_ever_done: Dict[str, bool] = {m: False for m in MARKETS}
        self.buy6_anchor: Dict[str, Optional[Decimal]] = {m: None for m in MARKETS}
        self.pending_buys: Dict[str, Dict[int, dict]] = {m: {} for m in MARKETS}
        # Флаг для предотвращения дублирования BUY1
        self.buy1_in_progress: Dict[str, bool] = {m: False for m in MARKETS}

        self._load_state()

    # ---------- state ----------
    def _load_state(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for m in MARKETS:
                self.buy1_ever_done[m] = bool(data.get("buy1_ever_done", {}).get(m, False))
                if self.buy1_ever_done[m]:
                    self.buy1_done[m] = True
        except Exception:
            pass

    async def restore_branches_from_position(self, symbol: str):
        """Восстанавливает ветки на основе существующей позиции"""
        size, wap = await self.position(symbol)
        if size <= 0:
            return
        
        self.log(symbol, f"🔄 Восстанавливаем ветки из позиции: size={size}, WAP={wap}")
        
        # Создаем ветку на основе существующей позиции
        b_id = self.new_branch_id(symbol)
        stop = rprice(symbol, wap * (Decimal("1") + Decimal(str(BRANCH_SL_PCT))))
        
        # Создаем sell legs
        legs = {}
        for leg_name, tp, split in zip(("L1","L2","L3"), SELL_STEPS_PCT, SELL_SPLIT):
            legs[leg_name] = SellLeg(leg=leg_name, target_pct=Decimal(str(tp)), size=rsize(symbol, size * Decimal(str(split))))
        
        # Создаем ветку
        self.branches[symbol][b_id] = Branch(
            branch_id=b_id, symbol=symbol, buy_price=wap, size=size, wap=wap, stop_price=stop, active=True, sells=legs
        )
        
        self.log(symbol, f"✅ Восстановлена ветка {b_id}: size={size}, buy={wap}, SL={stop}")
        
        # Устанавливаем флаги
        self.buy1_done[symbol] = True
        self.buy1_ever_done[symbol] = True
        
        # Якорь BUY6+ НЕ устанавливаем здесь - он будет установлен в maybe_buy6
        # на текущую цену для правильного отслеживания минимума
        self.buy6_anchor[symbol] = None

    def _save_state(self):
        data = {"buy1_ever_done": self.buy1_ever_done}
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    async def stats(self, symbol: str):
        return await self.c.markets_info.get_market_statistics(market_name=symbol)

    async def best_bid_ask(self, symbol: str):
        st = await self.stats(symbol)
        bid = getattr(st.data, "bid_price", None) or getattr(st.data, "best_bid", None)
        ask = getattr(st.data, "ask_price", None) or getattr(st.data, "best_ask", None)
        return Decimal(str(bid)), Decimal(str(ask))

    async def last_price(self, symbol: str) -> Decimal:
        st = await self.stats(symbol)
        lp = getattr(st.data, "last_price", None) or getattr(st.data, "mark_price", None)
        return Decimal(str(lp))

    async def position(self, symbol: str):
        res = await self.c.account.get_positions(market_names=[symbol], position_side=PositionSide.LONG)
        size = Decimal("0"); wap = Decimal("0")
        for p in (res.data or []):
            sz = getattr(p, "size", Decimal(0))
            if sz and Decimal(str(sz)) > 0:
                size = Decimal(str(sz)); wap = Decimal(str(getattr(p, "open_price", 0))); break
        return size, wap

    async def open_orders(self, symbol: str, side: Optional[OrderSide]=None):
        kw = {"market_names":[symbol]}
        if side:
            kw["order_side"] = side
        res = await self.c.account.get_open_orders(**kw)
        return res.data or []

    async def place_limit(self, symbol: str, side: OrderSide, price: Decimal, size: Decimal, client_id: str, ttl_seconds: Optional[int] = None) -> Optional[int]:
        import datetime
        expire_time = None
        if ttl_seconds:
            expire_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=ttl_seconds)
        resp = await self.c.place_order(
            market_name=symbol,
            amount_of_synthetic=size,
            price=price,
            side=side,
            time_in_force=TimeInForce.GTT,
            external_id=client_id,
            expire_time=expire_time,
        )
        return int(resp.data.id) if resp and getattr(resp, "data", None) else None

    async def place_market_sell_ioc(self, symbol: str, size: Decimal, client_id: str):
        last = await self.last_price(symbol)
        resp = await self.c.place_order(
            market_name=symbol,
            amount_of_synthetic=size,
            price=last,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.IOC,
            external_id=client_id
        )
        return int(resp.data.id) if resp and getattr(resp, "data", None) else None

    async def cancel_order(self, order_id: int):
        await self.c.orders.cancel_order(order_id=order_id)

    def log(self, s: str, msg: str):
        print(f"[{s}] {msg}", flush=True)

    def new_branch_id(self, symbol: str) -> int:
        bid = self.next_branch_id[symbol]; self.next_branch_id[symbol] += 1; return bid

    def has_active(self, symbol: str) -> bool:
        return any(b.active and b.size > 0 for b in self.branches[symbol].values())

    async def maybe_buy1(self, symbol: str):
        # Проверяем все возможные условия для предотвращения дублирования
        if self.buy1_ever_done[symbol]:
            return
        if self.buy1_done[symbol] or self.has_active(symbol):
            return
        
        # Проверяем, не выполняется ли уже BUY1
        if self.buy1_in_progress[symbol]:
            self.log(symbol, f"🔒 BUY1 заблокирован - уже выполняется")
            return
        
        # Проверяем, нет ли уже висячих BUY1 ордеров
        existing_buy1 = any(
            meta.get("kind") == "BUY1" 
            for meta in self.pending_buys[symbol].values()
        )
        if existing_buy1:
            self.log(symbol, f"🔒 BUY1 заблокирован - уже есть висячий ордер")
            return
        
        # Устанавливаем флаг блокировки АТОМАРНО
        self.buy1_in_progress[symbol] = True
        self.log(symbol, f"🔒 Устанавливаем блокировку BUY1")
        
        try:
            bid, _ = await self.best_bid_ask(symbol)
            price = rprice(symbol, bid)
            size = rsize(symbol, Decimal(str(BUY_QTY[symbol])))
            self.log(symbol, f"🔍 Попытка BUY1: size={size}, price={price}")
            cid = f"{symbol}:BRNEW:BUY1:{uuid.uuid4().hex[:8]}"
            oid = await self.place_limit(symbol, OrderSide.BUY, price, size, cid, ttl_seconds=BUY_TTL_SECONDS)
            if oid:
                self.pending_buys[symbol][oid] = {"price": price, "size": size, "client_id": cid, "ts": asyncio.get_event_loop().time(), "kind": "BUY1"}
                self.log(symbol, f"🟢 BUY1 размещён {size}@{price} TTL={BUY_TTL_SECONDS}s")
            else:
                # Если не удалось разместить ордер, снимаем блокировку
                self.buy1_in_progress[symbol] = False
                self.log(symbol, f"❌ Не удалось разместить BUY1, снимаем блокировку")
        except Exception as e:
            # В случае ошибки обязательно снимаем блокировку
            self.buy1_in_progress[symbol] = False
            self.log(symbol, f"❌ Ошибка при размещении BUY1: {e}, снимаем блокировку")
            raise

    async def maybe_buy6(self, symbol: str, last: Decimal):
        if not self.buy1_done[symbol]:
            return
        
        anchor = self.buy6_anchor[symbol]
        if anchor is None:
            # Устанавливаем якорь на текущую цену (это будет минимум после BUY1)
            self.buy6_anchor[symbol] = last
            self.log(symbol, f"🎯 Устанавливаем якорь BUY6+ на минимум: {last}")
            return
        
        # Обновляем якорь если цена упала ниже текущего якоря
        if last < anchor:
            self.buy6_anchor[symbol] = last
            self.log(symbol, f"📉 Обновляем якорь BUY6+ на новый минимум: {last}")
        
        # Используем обновленный якорь для расчета триггера
        current_anchor = self.buy6_anchor[symbol]
        trigger = current_anchor * (Decimal("1") + Decimal(str(BUY6_STEP_PCT)))
        self.log(symbol, f"🎯 BUY6+ проверка: цена={last}, якорь={current_anchor}, триггер={trigger}")
        
        # Размещаем BUY6+ только когда цена >= триггера
        if last >= trigger:
            # Проверяем, нет ли уже активного BUY6+ ордера
            existing_buy6 = any(
                meta.get("kind") == "BUY6" 
                for meta in self.pending_buys[symbol].values()
            )
            if existing_buy6:
                self.log(symbol, f"🔒 BUY6+ уже размещен, ждем исполнения")
                return
            
            bid, _ = await self.best_bid_ask(symbol)
            price = rprice(symbol, bid)
            size = rsize(symbol, Decimal(str(BUY_QTY[symbol])))
            cid = f"{symbol}:BRNEW:BUY6:{uuid.uuid4().hex[:8]}"
            oid = await self.place_limit(symbol, OrderSide.BUY, price, size, cid, ttl_seconds=180)  # 3 минуты TTL для BUY6+
            if oid:
                self.pending_buys[symbol][oid] = {"price": price, "size": size, "client_id": cid, "ts": asyncio.get_event_loop().time(), "kind": "BUY6"}
                # После размещения BUY6+ устанавливаем новый якорь на текущую цену
                self.buy6_anchor[symbol] = last
                self.log(symbol, f"🟢 BUY6+ размещён {size}@{price}; новый якорь={last}")
        else:
            self.log(symbol, f"🔍 BUY6+ не сработал: {last} < {trigger}")

    async def enforce_buy_ttls(self, symbol: str):
        if not self.pending_buys[symbol]:
            return
        opens = await self.open_orders(symbol, side=OrderSide.BUY)
        open_map = {int(getattr(o, "id")): o for o in opens}
        now = asyncio.get_event_loop().time()
        to_delete = []
        
        for oid, meta in list(self.pending_buys[symbol].items()):
            o = open_map.get(int(oid))
            age = now - meta["ts"]
            kind = meta.get("kind", "BUY")
            
            # Определяем TTL в зависимости от типа ордера
            ttl_seconds = 180 if kind == "BUY6" else BUY_TTL_SECONDS  # BUY6: 3 мин, BUY1: 5 мин
            
            # Сначала проверяем исполнение ордера
            if o is None:
                # Ордер не найден на бирже - проверяем, есть ли позиция
                pos_size, pos_wap = await self.position(symbol)
                if pos_size > 0:
                    # Есть позиция - ордер исполнен
                    await self.on_buy_filled(symbol, price=meta["price"], size=meta["size"], kind=kind)
                    self.log(symbol, f"✅ BUY исполнен → создаем ветку: size={meta['size']}, buy={meta['price']}")
                else:
                    # Нет позиции - ордер истек или был отменен
                    self.log(symbol, f"⚠️ BUY ордер не найден и позиции нет: {meta['size']}@{meta['price']} ({kind})")
                to_delete.append(oid)
                continue
            
            # Проверяем частичное исполнение
            filled = Decimal(str(getattr(o, "filled_qty", 0) or 0))
            qty = Decimal(str(getattr(o, "qty", 0) or 0))
            if qty > 0 and filled >= qty:
                await self.on_buy_filled(symbol, price=meta["price"], size=meta["size"], kind=kind)
                to_delete.append(oid)
            elif filled > 0:
                self.log(symbol, f"⏳ BUY частично исполнен {filled}/{qty}, ждём заполнения")
            elif age >= ttl_seconds:
                # Проверяем TTL только если ордер не исполнен
                try:
                    await self.cancel_order(int(oid))
                    self.log(symbol, f"🟡 Отменяем {kind} (TTL {ttl_seconds}s) {meta['size']}@{meta['price']}")
                    
                    # Если это BUY1 ордер, снимаем блокировку для переразмещения
                    if kind == "BUY1":
                        self.buy1_in_progress[symbol] = False
                        self.log(symbol, f"🔓 Снимаем блокировку BUY1 после отмены по TTL для переразмещения")
                    
                except Exception as e:
                    self.log(symbol, f"❌ Ошибка отмены {kind} {oid}: {e}")
                    # В случае ошибки отмены тоже снимаем блокировку для BUY1
                    if kind == "BUY1":
                        self.buy1_in_progress[symbol] = False
                        self.log(symbol, f"🔓 Снимаем блокировку BUY1 после ошибки отмены")
                
                # Переразмещаем ордер ближе к рынку
                bid, _ = await self.best_bid_ask(symbol)
                new_price = rprice(symbol, bid)
                new_cid = ":".join(meta["client_id"].split(":")[:-1] + [uuid.uuid4().hex[:8]])
                new_oid = await self.place_limit(symbol, OrderSide.BUY, new_price, meta["size"], new_cid, ttl_seconds=ttl_seconds)
                if new_oid:
                    self.pending_buys[symbol][new_oid] = {"price": new_price, "size": meta["size"], "client_id": new_cid, "ts": now, "kind": kind}
                    self.log(symbol, f"🔁 Переразмещаем {kind} ближе к рынку: {meta['size']}@{new_price}")
                to_delete.append(oid)
        
        for oid in to_delete:
            self.pending_buys[symbol].pop(oid, None)

    async def on_buy_filled(self, symbol: str, price: Decimal, size: Decimal, kind: str = "BUY"):
        # Проверяем, есть ли уже активная ветка с такими же параметрами
        existing_branch = None
        for b in self.branches[symbol].values():
            if b.active and b.size == size and abs(b.wap - price) < Decimal("0.01"):
                existing_branch = b
                self.log(symbol, f"✅ Найдена существующая активная ветка {b.branch_id}, не создаем дублирующую")
                break
        
        if existing_branch:
            # Если это BUY1, все равно снимаем блокировку
            if kind == "BUY1" and not self.buy1_done[symbol]:
                self.buy1_done[symbol] = True
                self.buy1_ever_done[symbol] = True
                self._save_state()
                self.buy6_anchor[symbol] = price
                self.log(symbol, "📌 BUY1 подтверждён: включаем BUY6+ и сохраняем флаг навсегда")
                self.buy1_in_progress[symbol] = False
            return
        
        if not self.buy1_done[symbol]:
            self.buy1_done[symbol] = True
            self.buy1_ever_done[symbol] = True
            self._save_state()
            self.buy6_anchor[symbol] = price
            self.log(symbol, "📌 BUY1 подтверждён: включаем BUY6+ и сохраняем флаг навсегда")
            # Снимаем блокировку BUY1 после успешного исполнения
            self.buy1_in_progress[symbol] = False
        
        b_id = self.new_branch_id(symbol)
        stop = rprice(symbol, price * (Decimal("1") + Decimal(str(BRANCH_SL_PCT))))
        legs = {}
        for leg_name, tp, split in zip(("L1","L2","L3"), SELL_STEPS_PCT, SELL_SPLIT):
            legs[leg_name] = SellLeg(leg=leg_name, target_pct=Decimal(str(tp)), size=rsize(symbol, size * Decimal(str(split))))
        self.branches[symbol][b_id] = Branch(
            branch_id=b_id, symbol=symbol, buy_price=price, size=size, wap=price, stop_price=stop, active=True, sells=legs
        )
        self.log(symbol, f"✅ BUY исполнен → ветка {b_id}: size={size}, buy={price}, SL={stop} ({kind})")

    async def ensure_branch_sells(self, symbol: str):
        # Проверяем реальную позицию на бирже
        pos_size, pos_wap = await self.position(symbol)
        
        # Добавляем логирование для отладки
        active_branches = [b for b in self.branches[symbol].values() if b.active and b.size > 0]
        if active_branches:
            self.log(symbol, f"🔍 Проверяем {len(active_branches)} активных веток для sell ордеров")
        else:
            self.log(symbol, f"⚠️ Нет активных веток для размещения sell ордеров")
            return
        
        # Если нет реальной позиции, не размещаем sell ордера
        if pos_size <= 0:
            self.log(symbol, f"⚠️ Нет реальной позиции на бирже (pos={pos_size}), не размещаем sell ордера")
            return
        
        self.log(symbol, f"📊 Реальная позиция: {pos_size} BTC по цене {pos_wap}")
        
        opens = await self.open_orders(symbol, side=OrderSide.SELL)
        open_by_cid = {str(getattr(o, "external_id", "") or ""): o for o in opens}

        for b in list(self.branches[symbol].values()):
            if not b.active or b.size <= 0:
                continue
            pnl_floor = (b.wap or pos_wap) * (Decimal("1") + Decimal(str(PNL_MIN_PCT)))

            placed_total = Decimal("0")
            for leg in b.sells.values():
                if leg.client_id and leg.client_id in open_by_cid:
                    placed_total += Decimal(str(getattr(open_by_cid[leg.client_id], "qty", 0) or 0))

            for leg_name, leg in b.sells.items():
                target = b.buy_price * (Decimal("1") + leg.target_pct)
                min_price = rprice(symbol, max(target, pnl_floor))

                existing = open_by_cid.get(leg.client_id or "")
                if existing:
                    ex_price = Decimal(str(getattr(existing, "price", 0) or 0))
                    if ex_price < min_price:
                        try:
                            await self.cancel_order(int(getattr(existing, "id")))
                            self.log(symbol, f"✏️ Повышаем SELL {leg_name} ветки {b.branch_id}: отмена {ex_price} < {min_price}")
                        except Exception as e:
                            self.log(symbol, f"❌ Ошибка отмены SELL {leg_name}: {e}")
                        existing = None
                    else:
                        continue

                remaining = b.size - placed_total
                if remaining <= 0:
                    continue
                place_size = min(leg.size, remaining)
                if place_size <= 0:
                    continue
                cid = f"{symbol}:BR{b.branch_id}:S:{leg_name}:{uuid.uuid4().hex[:6]}"
                oid = await self.place_limit(symbol, OrderSide.SELL, min_price, rsize(symbol, place_size), cid, ttl_seconds=None)
                if oid:
                    leg.client_id = cid; leg.order_id = oid; leg.price = min_price
                    placed_total += place_size
                    self.log(symbol, f"🟠 SELL {leg_name} ветки {b.branch_id} {place_size}@{min_price} (≥PnL)")

    async def dedupe_branch_sells(self, symbol: str, b: Branch):
        opens = await self.open_orders(symbol, side=OrderSide.SELL)
        branch_sells = [o for o in opens if str(getattr(o, "external_id", "")).startswith(f"{symbol}:BR{b.branch_id}:S:")]
        total = sum(Decimal(str(getattr(o, "qty", 0) or 0)) for o in branch_sells)
        if total <= b.size:
            return
        branch_sells.sort(key=lambda o: Decimal(str(getattr(o, "price", 0) or 0)))
        excess = total - b.size; cancelled = Decimal("0")
        for o in branch_sells:
            if cancelled >= excess:
                break
            try:
                await self.cancel_order(int(getattr(o, "id")))
                cancelled += Decimal(str(getattr(o, "qty", 0) or 0))
                self.log(symbol, f"🧹 Отменили лишний SELL ветки {b.branch_id}: {getattr(o,'id')} {getattr(o,'qty')}@{getattr(o,'price')}")
            except Exception as e:
                self.log(symbol, f"❌ Ошибка отмены лишнего SELL: {e}")

    async def _market_close_branch(self, symbol: str, b: Branch, last: Decimal):
        rem = rsize(symbol, b.size)
        if rem <= 0:
            b.active = False; return
        
        cid = f"{symbol}:BR{b.branch_id}:SL:{uuid.uuid4().hex[:6]}"
        try:
            pre_pos, _ = await self.position(symbol)
            oid = await self.place_market_sell_ioc(symbol, rem, cid)
            self.log(symbol, f"🛑 SL ветки {b.branch_id}: market IOC {rem} (oid={oid})")
        except Exception as e:
            self.log(symbol, f"❌ Ошибка отправки SL market ветки {b.branch_id}: {e}")
            return

        # Ждем исполнения stop-loss ордера
        try:
            target_dec = min(rem, pre_pos)
            deadline = asyncio.get_event_loop().time() + 15.0  # Увеличиваем время ожидания
            while True:
                await asyncio.sleep(0.5)
                cur_pos, _ = await self.position(symbol)
                
                # Проверяем, уменьшилась ли позиция
                if cur_pos <= pre_pos - target_dec * Decimal("0.99") or cur_pos <= Decimal("0"):
                    self.log(symbol, f"✅ SL исполнен: позиция уменьшилась с {pre_pos} до {cur_pos}")
                    break
                
                # Проверяем, не истекло ли время ожидания
                if asyncio.get_event_loop().time() >= deadline:
                    self.log(symbol, f"⏰ SL ожидание истекло: позиция {cur_pos} не уменьшилась достаточно")
                    break
        except Exception as e:
            self.log(symbol, f"⚠️ SL ожидание позиции: {e}")

        # После SL: если позиции нет, отменяем SELL ордера для ветки и деактивируем её
        cur_pos, _ = await self.position(symbol)
        if cur_pos <= Decimal("0"):
            opens = await self.open_orders(symbol, side=OrderSide.SELL)
            cancelled_count = 0
            for o in opens:
                if str(getattr(o, "external_id", "")).startswith(f"{symbol}:BR{b.branch_id}:S:"):
                    try:
                        await self.cancel_order(int(getattr(o, "id")))
                        cancelled_count += 1
                        self.log(symbol, f"❌ Отменён SELL ветки {b.branch_id}: {getattr(o,'id')} (после SL market)")
                    except Exception as e:
                        self.log(symbol, f"❌ Ошибка отмены SELL ветки {b.branch_id} после SL: {e}")
            self.log(symbol, f"🧹 Отменено {cancelled_count} sell ордеров для ветки {b.branch_id}")
            b.active = False
        else:
            # Позиция не закрыта полностью — принудительно закрываем остаток по маркету
            self.log(symbol, f"🔄 После SL позиция осталась {cur_pos}, принудительно закрываем по маркету")
            try:
                force_cid = f"{symbol}:BR{b.branch_id}:SL_FORCE:{uuid.uuid4().hex[:6]}"
                force_oid = await self.place_market_sell_ioc(symbol, cur_pos, force_cid)
                self.log(symbol, f"🛑 Принудительное закрытие позиции: {cur_pos} (oid={force_oid})")
                
                # Ждем закрытия позиции
                await asyncio.sleep(2.0)
                final_pos, _ = await self.position(symbol)
                if final_pos <= Decimal("0"):
                    self.log(symbol, f"✅ Позиция полностью закрыта принудительным SL")
                else:
                    self.log(symbol, f"⚠️ Позиция не закрылась полностью: {final_pos}")
            except Exception as e:
                self.log(symbol, f"❌ Ошибка принудительного закрытия позиции: {e}")
            
            # В любом случае отменяем SELL и деактивируем ветку после принудительного SL
            opens = await self.open_orders(symbol, side=OrderSide.SELL)
            cancelled_count = 0
            for o in opens:
                if str(getattr(o, "external_id", "")).startswith(f"{symbol}:BR{b.branch_id}:S:"):
                    try:
                        await self.cancel_order(int(getattr(o, "id")))
                        cancelled_count += 1
                        self.log(symbol, f"❌ Отменён SELL ветки {b.branch_id}: {getattr(o,'id')} (после принудительного SL)")
                    except Exception as e:
                        self.log(symbol, f"❌ Ошибка отмены SELL ветки {b.branch_id} после принудительного SL: {e}")
            self.log(symbol, f"🧹 Отменено {cancelled_count} sell ордеров для ветки {b.branch_id}")
            b.active = False

    async def cleanup_orphan_sell_orders(self, symbol: str):
        """Независимая проверка: если позиции нет, отменяем все SELL ордера по символу и деактивируем ветки."""
        size, _ = await self.position(symbol)
        if size > 0:
            return
        opens = await self.open_orders(symbol, side=OrderSide.SELL)
        cancelled = 0
        for o in opens:
            try:
                await self.cancel_order(int(getattr(o, "id")))
                cancelled += 1
            except Exception as e:
                self.log(symbol, f"❌ Ошибка отмены SELL без позиции: {e}")
        if cancelled:
            self.log(symbol, f"🧹 Отменили {cancelled} SELL ордеров, т.к. позиции нет")
        # Деактивируем ветки без позиции
        for b in self.branches[symbol].values():
            b.active = False

    async def check_branch_sl(self, symbol: str, last: Decimal):
        # Проверяем стоп-лосс только если есть активные позиции
        if not self.has_active(symbol):
            return
            
        to_close = []
        for b in self.branches[symbol].values():
            if b.active and last <= b.stop_price:
                to_close.append(b)
        
        if not to_close:
            return
            
        self.log(symbol, f"🚨 SL: сработал у {len(to_close)} веток → market-first")
        
        for b in to_close:
            await self._market_close_branch(symbol, b, last)
        
        # Сбрасываем якорь BUY6+ для возможности новых покупок
        self.buy6_anchor[symbol] = None
        self.log(symbol, "♻️ После SL: BUY6+ anchor сброшен, готов к новым покупкам")

    async def run_once(self, symbol: str):
        last = await self.last_price(symbol)
        size, wap = await self.position(symbol)
        self.log(symbol, f"📈 last={last} | pos={size} WAP={wap}")
        
        # 1) Проверка стоп-лосса — независимая
        await self.check_branch_sl(symbol, last)
        
        # 2) Восстановление веток: только если есть позиция и активных веток нет — независимая
        active_branches = [b for b in self.branches[symbol].values() if b.active]
        if size > 0 and not active_branches:
            self.log(symbol, f"🔄 Обнаружена позиция без активных веток, восстанавливаем ветки и SELL ордера")
            await self.restore_branches_from_position(symbol)
        
        # 3) Торговая логика
        await self.maybe_buy1(symbol)
        await self.maybe_buy6(symbol, last)
        await self.ensure_branch_sells(symbol)
        for b in self.branches[symbol].values():
            if b.active:
                await self.dedupe_branch_sells(symbol, b)
        
        # 4) Независимая очистка: если позиции нет — отменяем SELL и деактивируем ветки
        await self.cleanup_orphan_sell_orders(symbol)
        
        # 5) TTL для buy ордеров — независимая
        await self.enforce_buy_ttls(symbol)

    async def run(self):
        # Восстанавливаем ветки из существующих позиций при запуске
        for symbol in MARKETS:
            await self.restore_branches_from_position(symbol)
        
        while True:
            try:
                await asyncio.gather(*(self.run_once(m) for m in MARKETS))
            except Exception as e:
                print("Loop error:", e, flush=True)
            await asyncio.sleep(TICK_SECONDS)

async def main():
    account = StarkPerpetualAccount(
        vault=VAULT_ID,
        private_key=STARK_PRIVATE_KEY,
        public_key=STARK_PUBLIC_KEY,
        api_key=API_KEY,
    )
    client = PerpetualTradingClient(STARKNET_MAINNET_CONFIG, account)
    bot = Bot(client)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
