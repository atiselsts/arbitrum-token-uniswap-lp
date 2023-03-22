#!/usr/bin/env python3

import os
from web3 import Web3
from abi import pool_abi
from collections import namedtuple

# hardcode ETH price for now
ETH_PRICE = 1800

Tick = namedtuple("Tick", "liquidityGross liquidityNet feeGrowthOutside0X128 feeGrowthOutside1X128 tickCumulativeOutside secondsPerLiquidityOutsideX128 secondsOutside initialized")

ARBITRUM_URL = os.getenv("PROVIDER_URL_ARBITRUM")

web3 = Web3(Web3.HTTPProvider(ARBITRUM_URL))

weth_pool_address = "0x92fd143A8FA0C84e016C2765648B9733b0aa519e" # 1% WETH/ARB pool
usdc_pool_address = "0xa8328bF492Ba1B77aD6381B3F7567D942b000baf" # 1% USDC/ARB pool

SPACING = 200

#
# Calculate x and y given liquidity and price range
#
def calculate_x(L, sp, sa, sb):
    sp = max(min(sp, sb), sa)     # if the price is outside the range, use the range endpoints instead
    return L * (sb - sp) / (sp * sb)

def calculate_y(L, sp, sa, sb):
    sp = max(min(sp, sb), sa)     # if the price is outside the range, use the range endpoints instead
    return L * (sp - sa)

def tick_to_price(tick):
    return 1.0001 ** tick

def eth_price(raw_price):
    return 1 / (raw_price / ETH_PRICE)

def usdc_price(raw_price):
    return raw_price * 1e12


def print_pool(pool_address, first_tick, last_tick, token_symbol, token_decimals, adjust_price, arb_first):
    pool_contract = web3.eth.contract(address=pool_address, abi=pool_abi)
    slot0 = pool_contract.functions.slot0().call()
    s_price = slot0[0] / (1 << 96)
    tick = slot0[1]
    print(f"current tick={tick} price={adjust_price(s_price ** 2):.2f} USDC/ARB")

    total_buy_amount = 0
    liquidity = 0
    if arb_first:
        step = -SPACING
    else:
        step = SPACING
    for tick in range(first_tick, last_tick, step):
        tick_data = Tick(*pool_contract.functions.ticks(tick).call())
        if tick_data.initialized:
            if arb_first:
                liquidity -= tick_data.liquidityNet
            else:
                liquidity += tick_data.liquidityNet
            assert liquidity >= 0
            s_price_a = tick_to_price(tick // 2)
            s_price_b = tick_to_price((tick + SPACING) // 2)
            x_amount = calculate_x(liquidity, s_price, s_price_a, s_price_b)
            y_amount = calculate_y(liquidity, s_price, s_price_a, s_price_b)
            mean_price = s_price_a * s_price_b
            if arb_first:
                sell_amount = y_amount
                buy_amount = sell_amount / mean_price
            else:
                sell_amount = x_amount
                buy_amount = sell_amount * mean_price
            total_buy_amount += buy_amount
            adjusted_sell = sell_amount / 10 ** token_decimals
            adjusted_buy = buy_amount / 1e18
            adjusted_price = adjust_price(mean_price)
            print(f"tick={tick} price={adjusted_price:.2f} USD/ARB, sell {adjusted_sell:.1f} {token_symbol} to buy {adjusted_buy:.0f} ARB")
    print(f"in total, the pool is buying {total_buy_amount/1e18:.0f} ARB")

if __name__ == "__main__":
    print("==========================================")
    print("WETH/ARB 1% pool")
    print("==========================================")
    print_pool(weth_pool_address, 71600, 90000, "ETH", 18, eth_price, False)

    print("==========================================")
    print("ARB/USDC 1% pool")
    print("==========================================")
    print_pool(usdc_pool_address, -230400, -300000, "USDC", 6, usdc_price, True)
