import asyncio
import os
import uuid
import json
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Optional

from dotenv import load_dotenv

from x10.perpetual.configuration import STARKNET_MAINNET_CONFIG
from x10.perpetual.trading_client.trading_client import PerpetualTradingClient
from x10.perpetual.accounts import StarkPerpetualAccount
from x10.perpetual.orders import OrderSide, TimeInForce
from x10.perpetual.positions import PositionSide

from config import MARKETS, BUY_QTY, PRICE_PRECISION, SIZE_PRECISION, TICK_SECONDS, MIN_ORDER_SIZES
from config import BUY_TTL_SECONDS, SELL_TTL_SECONDS, BUY6_STEP_PCT, SELL_STEPS_PCT, SELL_SPLIT, PNL_MIN_PCT, BRANCH_SL_PCT

load_dotenv()

API_KEY = os.getenv("EXTENDED_API_KEY")
STARK_PUBLIC_KEY = os.getenv("EXTENDED_PUBLIC_KEY")
STARK_PRIVATE_KEY = os.getenv("EXTENDED_STARK_PRIVATE")
VAULT_ID = int(os.getenv("EXTENDED_VAULT_ID")) if os.getenv("EXTENDED_VAULT_ID") else None

STATE_FILE = os.getenv("BOT_STATE_FILE", "bot_state.json")


def rprice(symbol: str, v: Decimal) -> Decimal:
    p = PRICE_PRECISION.get(symbol, 2)
    q = Decimal(10) ** (-p)
    return v.quantize(q)


def rsize(symbol: str, v: Decimal) -> Decimal:
    p = SIZE_PRECISION.get(symbol, 6)
    q = Decimal(10) ** (-p)
    vq = v.quantize(q)
    if vq == 0 and v > 0:
        return q

    min_size = Decimal(str(MIN_ORDER_SIZES.get(symbol, "0.0001")))

    if symbol == "BTC-USD":
        if vq < min_size:
            return min_size
        rounded = (vq / Decimal("0.0001")).quantize(Decimal("1")) * Decimal("0.0001")
        return max(rounded, min_size)

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
    created_at: Optional[datetime.datetime] = None
    last_updated: Optional[datetime.datetime] = None


class Bot:
    def __init__(self, client: PerpetualTradingClient):
        self.c = client
        self.branches: Dict[str, Dict[int, Branch]] = {m: {} for m in MARKETS}
        self.next_branch_id: Dict[str, int] = {m: 1 for m in MARKETS}

        # Якорь минимума для стратегии покупки на росте
        self.rise_anchor: Dict[str, Optional[Decimal]] = {m: None for m in MARKETS}

        # Висячие BUY ордера (переразмещение до полного fill)
        self.pending_buys: Dict[str, Dict[int, dict]] = {m: {} for m in MARKETS}

        self._load_state()

    # ---------- utils ----------
    def log(self, s: str, msg: str):
        print(f"[{s}] {msg}", flush=True)

    def new_branch_id(self, symbol: str) -> int:
        bid = self.next_branch_id[symbol]
        self.next_branch_id[symbol] += 1
        return bid

    def has_active(self, symbol: str) -> bool:
        return any(b.active and b.size > 0 for b in self.branches[symbol].values())

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

    async def open_orders(self, symbol: str, side: Optional[OrderSide] = None):
        kw = {"market_names": [symbol]}
        if side:
            kw["order_side"] = side
        res = await self.c.account.get_open_orders(**kw)
        return res.data or []

    async def cancel_order(self, order_id: int):
        await self.c.orders.cancel_order(order_id=order_id)

    async def place_limit(self, symbol: str, side: OrderSide, price: Decimal, size: Decimal, client_id: str,
                          ttl_seconds: Optional[int] = None) -> Optional[int]:
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
            external_id=client_id,
        )
        return int(resp.data.id) if resp and getattr(resp, "data", None) else None

    # ---------- state ----------
    def _save_state(self):
        data = {
            "branches": {},
            "next_branch_id": self.next_branch_id,
            "rise_anchor": {s: str(a) if a is not None else None for s, a in self.rise_anchor.items()},
        }
        for symbol in MARKETS:
            data["branches"][symbol] = {}
            for branch_id, branch in self.branches[symbol].items():
                data["branches"][symbol][branch_id] = {
                    "branch_id": branch.branch_id,
                    "symbol": branch.symbol,
                    "buy_price": str(branch.buy_price),
                    "size": str(branch.size),
                    "wap": str(branch.wap),
                    "stop_price": str(branch.stop_price),
                    "active": branch.active,
                    "created_at": branch.created_at.isoformat() if branch.created_at else None,
                    "last_updated": branch.last_updated.isoformat() if branch.last_updated else None,
                    "sells": {},
                }
                for leg_name, leg in branch.sells.items():
                    data["branches"][symbol][branch_id]["sells"][leg_name] = {
                        "leg": leg.leg,
                        "target_pct": str(leg.target_pct),
                        "size": str(leg.size),
                        "order_id": leg.order_id,
                        "client_id": leg.client_id,
                        "price": str(leg.price) if leg.price else None,
                    }

        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения состояния: {e}")

    def _load_state(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "rise_anchor" in data:
                for m in MARKETS:
                    raw = data["rise_anchor"].get(m)
                    self.rise_anchor[m] = Decimal(raw) if raw is not None else None

            if "branches" in data:
                for symbol in MARKETS:
                    if symbol in data["branches"]:
                        for branch_id, branch_data in data["branches"][symbol].items():
                            branch_id = int(branch_id)
                            b = Branch(
                                branch_id=branch_id,
                                symbol=branch_data["symbol"],
                                buy_price=Decimal(branch_data["buy_price"]),
                                size=Decimal(branch_data["size"]),
                                wap=Decimal(branch_data["wap"]),
                                stop_price=Decimal(branch_data["stop_price"]),
                                active=branch_data["active"],
                                created_at=datetime.datetime.fromisoformat(branch_data["created_at"]) if branch_data["created_at"] else None,
                                last_updated=datetime.datetime.fromisoformat(branch_data["last_updated"]) if branch_data["last_updated"] else None,
                            )
                            if "sells" in branch_data:
                                for leg_name, leg_data in branch_data["sells"].items():
                                    b.sells[leg_name] = SellLeg(
                                        leg=leg_name,
                                        target_pct=Decimal(leg_data["target_pct"]),
                                        size=Decimal(leg_data["size"]),
                                        order_id=leg_data.get("order_id"),
                                        client_id=leg_data.get("client_id"),
                                        price=Decimal(leg_data["price"]) if leg_data.get("price") else None,
                                    )
                            self.branches[symbol][branch_id] = b

            if "next_branch_id" in data:
                for symbol in MARKETS:
                    if symbol in data["next_branch_id"]:
                        self.next_branch_id[symbol] = data["next_branch_id"][symbol]
        except Exception as e:
            print(f"Ошибка загрузки состояния: {e}")

    def update_branch_timestamp(self, symbol: str, branch_id: int):
        if symbol in self.branches and branch_id in self.branches[symbol]:
            self.branches[symbol][branch_id].last_updated = datetime.datetime.now(datetime.timezone.utc)
            self.log(symbol, f"🕒 Обновлено время ветки {branch_id}")

    # ---------- logging helpers ----------
    def log_branch_state(self, symbol: str, b: Branch, note: str = ""):
        note_part = f" | {note}" if note else ""
        self.log(
            symbol,
            f"🌿 Ветка {b.branch_id}: size={b.size}, wap={b.wap}, SL={b.stop_price}, active={b.active}{note_part}"
        )

    # ИСПРАВЛЕНИЕ 2: Добавить детальное логирование расхождений
    async def log_position_mismatch(self, symbol: str):
        """Логирование расхождений между позицией и ветками"""
        total_branches = sum(b.size for b in self.branches[symbol].values() if b.active)
        real_pos, real_wap = await self.position(symbol)
        
        if abs(total_branches - real_pos) > Decimal("0.0001"):
            self.log(symbol, f"⚠️ РАСХОЖДЕНИЕ: ветки={total_branches}, позиция={real_pos}, разница={total_branches - real_pos}")
            
            # Детализация по веткам
            for b_id, b in self.branches[symbol].items():
                if b.active:
                    self.log(symbol, f"   Ветка {b_id}: size={b.size}, active={b.active}")
            
            return True
        return False

    # ИСПРАВЛЕНИЕ 2: Отслеживание исполнений селл ордеров
    async def track_sell_executions(self, symbol: str):
        """Отслеживание исполненных селл ордеров и корректировка размеров веток"""
        opens = await self.open_orders(symbol, side=OrderSide.SELL)
        open_by_cid = {getattr(o, "external_id", ""): o for o in opens}
        
        state_changed = False
        for b_id, b in list(self.branches[symbol].items()):
            if not b.active:
                continue
                
            total_executed = Decimal("0")
            for leg_name, leg in b.sells.items():
                if leg.client_id:
                    order = open_by_cid.get(leg.client_id)
                    if order:
                        # Ордер еще открыт
                        filled = Decimal(str(getattr(order, "filled_qty", 0) or 0))
                        total_executed += filled
                    else:
                        # Ордер исполнен или отменен - считаем полностью исполненным
                        if leg.order_id:  # Если был размещен
                            total_executed += leg.size
                            leg.order_id = None
                            leg.client_id = None
                            state_changed = True
            
            # Корректируем размер ветки на основе исполненных селлов
            if total_executed > 0 and total_executed < b.size:
                old_size = b.size
                b.size = rsize(symbol, b.size - total_executed)
                if b.size != old_size:
                    self.log(symbol, f"📉 Ветка {b_id}: размер {old_size} → {b.size} (исполнено SELL: {total_executed})")
                    self.update_branch_timestamp(symbol, b_id)
                    state_changed = True
            elif total_executed >= b.size:
                # Ветка полностью продана
                b.active = False
                self.log(symbol, f"✅ Ветка {b_id}: полностью продана ({total_executed})")
                self.update_branch_timestamp(symbol, b_id)
                state_changed = True
        
        if state_changed:
            self._save_state()

    # ---------- core: buy on rise ----------
    async def maybe_buy_on_rise(self, symbol: str, last: Decimal):
        anchor = self.rise_anchor[symbol]
        if anchor is None:
            self.rise_anchor[symbol] = last
            self.log(symbol, f"🎯 Устанавливаем якорь на минимум: {last}")
            return

        if last < anchor:
            self.rise_anchor[symbol] = last
            self.log(symbol, f"📉 Новый минимум: {last}")
            return

        trigger = anchor * (Decimal("1") + Decimal(str(BUY6_STEP_PCT[symbol])))
        self.log(symbol, f"🎯 Проверка роста: last={last}, anchor={anchor}, trigger={trigger}")
        if last < trigger:
            return

        # Не дублируем buy, если уже есть pending BUY
        if any(meta.get("kind") == "BUY" for meta in self.pending_buys[symbol].values()):
            self.log(symbol, "🔒 BUY уже размещён, ждём исполнения")
            return

        bid, _ = await self.best_bid_ask(symbol)
        price = rprice(symbol, bid)
        size = rsize(symbol, Decimal(str(BUY_QTY[symbol])))
        cid = f"{symbol}:RISE:{uuid.uuid4().hex[:8]}"
        pos_before, _ = await self.position(symbol)
        oid = await self.place_limit(symbol, OrderSide.BUY, price, size, cid, ttl_seconds=BUY_TTL_SECONDS)
        if oid:
            self.pending_buys[symbol][oid] = {
                "price": price,
                "size": size,
                "client_id": cid,
                "ts": asyncio.get_event_loop().time(),
                "kind": "BUY",
                "pos_before": pos_before,
            }
            # Сразу сдвигаем якорь на текущую цену, чтобы ждать нового минимума
            self.rise_anchor[symbol] = last
            self.log(symbol, f"🟢 BUY размещён {size}@{price}; anchor→{last}")

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
            ttl_seconds = BUY_TTL_SECONDS

            if o is None:
                pos_after, _ = await self.position(symbol)
                pos_before = Decimal(str(meta.get("pos_before", "0")))
                delta = pos_after - pos_before
                if delta >= meta["size"]:
                    # ИСПРАВЛЕНИЕ 1: Передаем реальный размер исполнения, а не размер ордера
                    await self.on_buy_filled(symbol, price=meta["price"], size=delta) 
                    self.log(symbol, f"✅ BUY полностью исполнен по позиции: +{delta} (было {meta['size']})")
                elif delta > 0:
                    # Частичное исполнение: создаем ветку на delta, переразмещаем остаток
                    await self.on_buy_filled(symbol, price=meta["price"], size=delta)
                    self.log(symbol, f"⚡ BUY частично исполнен: +{delta} из {meta['size']}")
                    remaining = rsize(symbol, meta["size"] - delta)
                    bid, _ = await self.best_bid_ask(symbol)
                    new_price = rprice(symbol, bid)
                    new_cid = ":".join(meta["client_id"].split(":")[:-1] + [uuid.uuid4().hex[:8]])
                    try:
                        new_oid = await self.place_limit(symbol, OrderSide.BUY, new_price, remaining, new_cid, ttl_seconds=ttl_seconds)
                    except Exception:
                        new_oid = None
                    if new_oid:
                        self.pending_buys[symbol][new_oid] = {
                            "price": new_price,
                            "size": remaining,
                            "client_id": new_cid,
                            "ts": now,
                            "kind": "BUY",
                            "pos_before": pos_after,
                        }
                        self.log(symbol, f"🔁 Переразмещаем BUY остаток {remaining}@{new_price}")
                else:
                    # Ордер пропал без исполнения - переразмещаем полный размер
                    bid, _ = await self.best_bid_ask(symbol)
                    new_price = rprice(symbol, bid)
                    new_cid = ":".join(meta["client_id"].split(":")[:-1] + [uuid.uuid4().hex[:8]])
                    try:
                        new_oid = await self.place_limit(symbol, OrderSide.BUY, new_price, rsize(symbol, meta["size"]), new_cid, ttl_seconds=ttl_seconds)
                    except Exception:
                        new_oid = None
                    if new_oid:
                        self.pending_buys[symbol][new_oid] = {
                            "price": new_price,
                            "size": rsize(symbol, meta["size"]),
                            "client_id": new_cid,
                            "ts": now,
                            "kind": "BUY",
                            "pos_before": pos_after,
                        }
                        self.log(symbol, f"🔁 Переразместили BUY {meta['size']}@{new_price}")
                to_delete.append(oid)
                continue

            filled = Decimal(str(getattr(o, "filled_qty", 0) or 0))
            qty = Decimal(str(getattr(o, "qty", 0) or 0))
            if qty > 0 and filled >= qty:
                # ИСПРАВЛЕНИЕ 1: При полном исполнении создаем ветку точно размера ордера
                await self.on_buy_filled(symbol, price=meta["price"], size=meta["size"])
                to_delete.append(oid)
            elif age >= ttl_seconds:
                try:
                    await self.cancel_order(int(oid))
                    self.log(symbol, f"🟡 Отменяем BUY (TTL {ttl_seconds}s) {meta['size']}@{meta['price']}")
                except Exception as e:
                    self.log(symbol, f"❌ Ошибка отмены BUY {oid}: {e}")

                # ИСПРАВЛЕНИЕ 4: Сохраняем текущую позицию для корректного pos_before
                current_pos, _ = await self.position(symbol)
                bid, _ = await self.best_bid_ask(symbol)
                new_price = rprice(symbol, bid)
                new_cid = ":".join(meta["client_id"].split(":")[:-1] + [uuid.uuid4().hex[:8]])
                try:
                    new_oid = await self.place_limit(symbol, OrderSide.BUY, new_price, meta["size"], new_cid, ttl_seconds=ttl_seconds)
                except Exception:
                    new_oid = None
                if new_oid:
                    self.pending_buys[symbol][new_oid] = {
                        "price": new_price,
                        "size": meta["size"],
                        "client_id": new_cid,
                        "ts": now,
                        "kind": "BUY",
                        "pos_before": current_pos,  # ИСПРАВЛЕНИЕ 4: Корректный pos_before
                    }
                    self.log(symbol, f"🔁 Переразмещаем BUY ближе к рынку: {meta['size']}@{new_price}")
                to_delete.append(oid)

        for oid in to_delete:
            self.pending_buys[symbol].pop(oid, None)

    async def on_buy_filled(self, symbol: str, price: Decimal, size: Decimal):
        b_id = self.new_branch_id(symbol)
        initial_stop = rprice(symbol, price * (Decimal("1") + Decimal(str(BRANCH_SL_PCT))))
        legs = {}
        for leg_name, tp, split in zip(("L1", "L2", "L3"), SELL_STEPS_PCT[symbol], SELL_SPLIT):
            legs[leg_name] = SellLeg(leg=leg_name, target_pct=Decimal(str(tp)), size=rsize(symbol, size * Decimal(str(split))))

        self.branches[symbol][b_id] = Branch(
            branch_id=b_id,
            symbol=symbol,
            buy_price=price,
            size=size,
            wap=price,
            stop_price=initial_stop,
            active=True,
            sells=legs,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            last_updated=datetime.datetime.now(datetime.timezone.utc),
        )
        self.log(symbol, f"🆕 Ветка {b_id}: buy={price}, size={size}, SL={initial_stop}")
        self.log_branch_state(symbol, self.branches[symbol][b_id], note="created")
        self._save_state()

    # ---------- sells ----------
    async def _ensure_branch_sells_for_branch(self, symbol: str, b: Branch, open_by_cid: dict):
        real_pos_size, _ = await self.position(symbol)
        if real_pos_size <= 0:
            self.log(symbol, f"🚫 Нет позиции для SELL ветки {b.branch_id}")
            return

        # Привязываем уже существующие SELL ордера (например, после рестарта), и дедуплицируем лишние
        state_changed = False
        for leg_name, leg in b.sells.items():
            leg_prefix = f"{symbol}:BR{b.branch_id}:S:{leg_name}:"
            # Находим все открытые ордера для этой ноги по префиксу external_id
            matching_cids = [cid for cid in open_by_cid.keys() if isinstance(cid, str) and cid.startswith(leg_prefix)]
            if matching_cids:
                # Если у ноги ещё нет client_id в состоянии – привязываем первый найденный ордер
                if not leg.client_id:
                    adopt_cid = matching_cids[0]
                    o = open_by_cid.get(adopt_cid)
                    if o:
                        leg.client_id = adopt_cid
                        leg.order_id = int(getattr(o, "id", 0) or 0) or None
                        leg.price = Decimal(str(getattr(o, "price", 0) or 0))
                        state_changed = True
                        self.log(symbol, f"🔗 Приняли существующий SELL {leg_name} ветки {b.branch_id}: {getattr(o,'qty',None)}@{getattr(o,'price',None)}")
                # Если найдено больше одного ордера для одной ноги – отменяем лишние
                if len(matching_cids) > 1:
                    # Сохраняем один (первый), остальные отменяем
                    for extra_cid in matching_cids[1:]:
                        o = open_by_cid.get(extra_cid)
                        try:
                            if o is not None:
                                await self.cancel_order(int(getattr(o, "id")))
                                self.log(symbol, f"🧹 Дедуп SELL {leg_name} ветки {b.branch_id}: отменяем лишний {getattr(o,'qty',None)}@{getattr(o,'price',None)}")
                        except Exception as e:
                            self.log(symbol, f"❌ Ошибка дедупликации SELL {leg_name} ветки {b.branch_id}: {e}")
        if state_changed:
            self.update_branch_timestamp(symbol, b.branch_id)
            self._save_state()

        # Если суммарный размер активных веток превышает позицию — масштабируем ветки пропорционально
        total_active = sum(x.size for x in self.branches[symbol].values() if x.active)
        if total_active > real_pos_size and total_active > 0:
            scale = (real_pos_size / total_active)
            new_size = rsize(symbol, b.size * Decimal(str(scale)))
            if new_size != b.size:
                b.size = new_size
                for i, (leg_name, leg) in enumerate(b.sells.items()):
                    leg.size = rsize(symbol, b.size * Decimal(str(SELL_SPLIT[i])))
                self.log(symbol, f"🔧 Масштабируем ветку {b.branch_id} до {b.size} (scale={scale:.4f})")
                self.update_branch_timestamp(symbol, b.branch_id)
                self.log_branch_state(symbol, b, note="scaled")

        # Сколько уже размещено в SELL для ветки
            placed_total = Decimal("0")
            for leg in b.sells.values():
                if leg.client_id and leg.client_id in open_by_cid:
                    placed_total += Decimal(str(getattr(open_by_cid[leg.client_id], "qty", 0) or 0))

        branch_wap = b.wap if b.wap else b.buy_price
        pnl_floor = branch_wap * (Decimal("1") + Decimal(str(PNL_MIN_PCT)))

            for leg_name, leg in b.sells.items():
            existing_order = open_by_cid.get(leg.client_id) if leg.client_id else None
            if existing_order:
                continue
            
            # PnL защита: селл ордера только выше WAP
                target = b.buy_price * (Decimal("1") + leg.target_pct)
            if target <= branch_wap:
                self.log(symbol, f"⚠️ Пропускаем {leg_name} - target {target} <= WAP {branch_wap}")
                        continue

            min_price = rprice(symbol, max(target, pnl_floor))
                remaining = b.size - placed_total
                if remaining <= 0:
                    continue
                place_size = min(leg.size, remaining)
                if place_size <= 0:
                    continue
                cid = f"{symbol}:BR{b.branch_id}:S:{leg_name}:{uuid.uuid4().hex[:6]}"
            oid = await self.place_limit(symbol, OrderSide.SELL, min_price, rsize(symbol, place_size), cid, ttl_seconds=SELL_TTL_SECONDS)
                if oid:
                leg.client_id = cid
                leg.order_id = oid
                leg.price = min_price
                    placed_total += place_size
                self.log(symbol, f"🟠 SELL {leg_name} ветки {b.branch_id} {place_size}@{min_price} (PnL защита: {pnl_floor})")
                self.update_branch_timestamp(symbol, b.branch_id)
                # Сохраняем client_id, чтобы не потерять связь после рестартов
                self._save_state()

    async def ensure_branch_sells(self, symbol: str):
        real_pos_size, _ = await self.position(symbol)
        if real_pos_size <= 0:
            self.log(symbol, f"🚫 Нет позиции для размещения SELL")
            return
        opens = await self.open_orders(symbol, side=OrderSide.SELL)
        open_by_cid = {getattr(o, "external_id", ""): o for o in opens}
        for b in self.branches[symbol].values():
            if b.active:
                await self._ensure_branch_sells_for_branch(symbol, b, open_by_cid)

    # ---------- stop-loss ----------
    async def _cancel_branch_sells(self, symbol: str, branch_id: int):
        opens = await self.open_orders(symbol, side=OrderSide.SELL)
        cancelled = 0
        for o in opens:
            client_id = str(getattr(o, "external_id", "") or "")
            if f":BR{branch_id}:S:" in client_id:
            try:
                await self.cancel_order(int(getattr(o, "id")))
                    cancelled += 1
            except Exception as e:
                    self.log(symbol, f"❌ Ошибка отмены SELL ветки {branch_id}: {e}")
        if cancelled:
            self.log(symbol, f"🧹 Отменено {cancelled} SELL для ветки {branch_id}")

    async def _market_close_branch(self, symbol: str, b: Branch):
        pre_pos, _ = await self.position(symbol)
        rem = rsize(symbol, min(b.size, pre_pos))
        if rem <= 0:
            await self._cancel_branch_sells(symbol, b.branch_id)
            b.active = False
            self.update_branch_timestamp(symbol, b.branch_id)
            self.log_branch_state(symbol, b, note="deactivated-no-pos")
            return

        cid = f"{symbol}:BR{b.branch_id}:SL:{uuid.uuid4().hex[:6]}"
        try:
            await self.place_market_sell_ioc(symbol, rem, cid)
            self.log(symbol, f"🛑 SL ветки {b.branch_id}: market IOC {rem}")
        except Exception as e:
            self.log(symbol, f"❌ Ошибка SL market ветки {b.branch_id}: {e}")
            return

        # Проверяем позицию спустя короткое ожидание
        await asyncio.sleep(1.0)
                cur_pos, _ = await self.position(symbol)
        if cur_pos <= Decimal("0"):
            await self._cancel_branch_sells(symbol, b.branch_id)
            b.active = False
            self.update_branch_timestamp(symbol, b.branch_id)
            self.log_branch_state(symbol, b, note="deactivated-after-sl")
        else:
            # Деактивируем ветку и отменяем её SELL, остаток позиции оставляем другим веткам
            await self._cancel_branch_sells(symbol, b.branch_id)
            b.active = False
            self.update_branch_timestamp(symbol, b.branch_id)
            self.log_branch_state(symbol, b, note="deactivated-force")

    async def check_sell_ttls(self, symbol: str):
        """Проверяет TTL селл ордеров и переразмещает их если нужно"""
        if not self.has_active(symbol):
            return

        opens = await self.open_orders(symbol, side=OrderSide.SELL)
        current_time = asyncio.get_event_loop().time()
        
        for o in opens:
            client_id = str(getattr(o, "external_id", "") or "")
            if ":BR" in client_id and ":S:" in client_id:
                # Извлекаем branch_id и leg_name из client_id
                parts = client_id.split(":")
                if len(parts) >= 4:
                    branch_id = int(parts[1][2:])  # BR{branch_id}
                    leg_name = parts[3]  # L1, L2, L3
                    
                    if branch_id in self.branches[symbol] and self.branches[symbol][branch_id].active:
                        branch = self.branches[symbol][branch_id]
                        if leg_name in branch.sells:
                            leg = branch.sells[leg_name]
                            
                            # Проверяем TTL
                            if hasattr(o, 'created_at') and o.created_at:
                                order_age = current_time - o.created_at.timestamp()
                                if order_age > SELL_TTL_SECONDS:
                                    self.log(symbol, f"⏰ TTL истек для SELL {leg_name} ветки {branch_id}, переразмещаем")
                                    
                                    # Отменяем старый ордер
                try:
                    await self.cancel_order(int(getattr(o, "id")))
                                        leg.client_id = None
                                        leg.order_id = None
                                        leg.price = None
                except Exception as e:
                                        self.log(symbol, f"❌ Ошибка отмены TTL SELL: {e}")
                                        continue
                                    
                                    # Переразмещаем с новым TTL
                                    await self._ensure_branch_sells_for_branch(symbol, branch, {})
                                    break  # Обрабатываем по одному за раз

    async def check_branch_sl(self, symbol: str, last: Decimal):
        if not self.has_active(symbol):
            return
        to_close = []
        for b in self.branches[symbol].values():
            if b.active and last <= b.stop_price:
                to_close.append(b)
        if not to_close:
            return
        ids = ",".join(str(x.branch_id) for x in to_close)
        self.log(symbol, f"🚨 SL: сработал у {len(to_close)} веток [{ids}]")
        for b in to_close:
            await self._market_close_branch(symbol, b)

    # ---------- main loop ----------
    async def run_once(self, symbol: str):
        last = await self.last_price(symbol)
        size, wap = await self.position(symbol)
        active_cnt = sum(1 for b in self.branches[symbol].values() if b.active)
        self.log(symbol, f"📈 last={last} | pos={size} WAP={wap} | branches={active_cnt}")

        # ИСПРАВЛЕНИЕ 5: При отсутствии позиции деактивируем ветки и сбрасываем их размер
        if size <= 0:
            for b in list(self.branches[symbol].values()):
                if b.active:
                    await self._cancel_branch_sells(symbol, b.branch_id)
                    b.active = False
                    b.size = Decimal("0")  # ИСПРАВЛЕНИЕ 5: Сбрасываем размер ветки
                    self.update_branch_timestamp(symbol, b.branch_id)
                    self.log(symbol, f"🔄 Ветка {b.branch_id}: деактивирована и сброшена (нет позиции)")

        # Покупка на росте
        await self.maybe_buy_on_rise(symbol, last)

        # ИСПРАВЛЕНИЕ 2: Отслеживание исполнений селл ордеров
        await self.track_sell_executions(symbol)
        
        # ИСПРАВЛЕНИЕ 2: Проверка расхождений
        await self.log_position_mismatch(symbol)

        # Размещение SELL не чаще, чем раз в 30 сек
        if not hasattr(self, "_last_sell_check"):
            self._last_sell_check = {}
        if symbol not in self._last_sell_check:
            self._last_sell_check[symbol] = 0
        now = asyncio.get_event_loop().time()
        if now - self._last_sell_check[symbol] >= 30:
            await self.ensure_branch_sells(symbol)
            self._last_sell_check[symbol] = now
            self.log(symbol, f"⏰ Проверка SELL ордеров (интервал: 30 сек)")
        else:
            remain = 30 - (now - self._last_sell_check[symbol])
            self.log(symbol, f"⏳ Пропускаем проверку SELL (осталось {remain:.1f} сек)")

        # SL проверка
        await self.check_branch_sl(symbol, last)

        # TTL SELL проверка
        await self.check_sell_ttls(symbol)

        # TTL BUY
        await self.enforce_buy_ttls(symbol)

    async def run(self):
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
