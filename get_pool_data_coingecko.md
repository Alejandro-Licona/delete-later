we need to get uniswap apys for these pools from January 1 2026 to March 12 2026

coingecko api key is CG-mCzA4y4DKC4cGd7T3dCV2UAt

here are the addresses of the pools we need: 
mainnet ETH/USDC pool: 0xdce6394339af00981949f5f3baf27e3610c76326a700af57e4b3e3ae4977f78d
mainnet ETH/USDT pool: 0x72331fcb696b0151904c03584b66dc8365bc63f8a144d89a773384e3a579ca73
mainnet WBTC/USDC pool: 0xb98437c7ba28c6590dd4e1cc46aa89eed181f97108e5b6221730d41347bc817f
mainnet USDC/cbBTC pool: 0x7067a500ad68cf5129b957fa62c97042cddccaa15d16cb91e3720d97971109bb
mainnet WBTC/USDT pool: 0x20c3a15e34e5d88aeba004b0753af69e4f6bea80eae2263f7a92e919cd33cc56

arbitrum ETH/USDC pool: 0x864abca0a6202dba5b8868772308da953ff125b0f95015adbf89aaf579e903a8
arbitrum ETH/USDT pool: 0xe88bba0ec2fc9091d68344b32b504abcc59f0aa9e1ae2ef048b69bc7ec3f4df8
arbitrum WBTC/USDC pool: 0x80c735c5a0222241f211b3edb8df2ccefad94553ec18f1c29143f0399c78f500
arbitrum WBTC/USDT pool: 0x41b1e6b28a39199365f5348a2bf71d0f785167e920d05254b3f2efd1b9487db5

unichain ETH/USDC pool: 0x3258f413c7a88cda2fa8709a589d221a80f6574f63df5a5b6774485d8acc39d9
unichain ETH/USDT pool: 0x04b7dd024db64cfbe325191c818266e4776918cd9eaf021c26949a859e654b16
unichain WBTC/USDC pool: 0xbd0f3a7cf4cf5f48ebe850474c8c0012fa5fe893ab811a8b8743a52b83aa8939
unichain WBTC/USDT pool: 0x05dbb214bd7b9461f9c2f6690b612629b65b9f81d7312fdd3e552d2dda85f771

> ## Documentation Index
> Fetch the complete documentation index at: https://docs.coingecko.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Specific Pool Data by Pool Address

> This endpoint allows you to **query the specific pool based on the provided network and pool address**

<Note>
  ### Note

  * Address not found in GeckoTerminal will be ignored.
  * If the token's market cap is not verified by the team, the API response will return `null` for its market cap value, even though it has a displayed value on GeckoTerminal, which might not be accurate as it often matches the Fully Diluted Valuation (FDV).
  * Market Cap can be verified by and sourced from CoinGecko, and the number may be higher than FDV as it may include Market Cap of tokens issued on other blockchain network.
  * Attributes specified in the `include` param will be returned under the top-level "included" key.
  * `locked_liquidity_percentage` will be updated on daily basis.
  * Set `include_composition=true` to surface the balance and liquidity value of the pool's base and quote tokens.
  * Pools on a bonding curve (e.g. non-graduated pools from launchpads) will return `launchpad_details` object with their graduation status and migration details.
  * Cache / Update Frequency: every 60 seconds.
</Note>


## OpenAPI

````yaml v3.0.1/reference/api-reference/onchain-demo.json get /networks/{network}/pools/{address}
openapi: 3.0.0
info:
  title: Onchain DEX API (Demo)
  version: 3.0.0
servers:
  - url: https://api.coingecko.com/api/v3/onchain
security:
  - apiKeyAuth: []
  - apiKeyQueryParam: []
paths:
  /networks/{network}/pools/{address}:
    get:
      tags:
        - Pools
      summary: Specific Pool Data by Pool Address
      description: >-
        This endpoint allows you to **query the specific pool based on the
        provided network and pool address**
      operationId: pool-address
      parameters:
        - name: network
          in: path
          description: |-
            network ID 
             *refers to [/networks](/v3.0.1/reference/networks-list)
          required: true
          schema:
            type: string
            example: eth
            default: eth
        - name: address
          in: path
          description: pool address
          required: true
          schema:
            type: string
            example: '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640'
            default: '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640'
        - name: include
          in: query
          required: false
          description: |-
            attributes to include, comma-separated if more than one to include 
             Available values: `base_token`, `quote_token`, `dex`
          schema:
            type: string
            default: base_token
          examples:
            one value:
              value: base_token
            multiple values:
              value: base_token,quote_token,dex
        - name: include_volume_breakdown
          in: query
          required: false
          description: 'include volume breakdown, default: false'
          schema:
            type: boolean
        - name: include_composition
          in: query
          required: false
          description: 'include pool composition, default: false'
          schema:
            type: boolean
      responses:
        '200':
          description: Get specific pool on a network
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SinglePoolInfo'
components:
  schemas:
    SinglePoolInfo:
      type: object
      properties:
        data:
          $ref: '#/components/schemas/PoolData'
        included:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              type:
                type: string
              attributes:
                type: object
                properties:
                  address:
                    type: string
                  name:
                    type: string
                  symbol:
                    type: string
                  decimals:
                    type: integer
                  image_url:
                    type: string
                  coingecko_coin_id:
                    type: string
      example:
        data:
          id: eth_0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640
          type: pool
          attributes:
            base_token_price_usd: '4473.69429892668'
            base_token_price_native_currency: '1.0'
            base_token_balance: '5713.28147604894'
            base_token_liquidity_usd: '25559474.76756355'
            quote_token_price_usd: '0.997996963545633'
            quote_token_price_native_currency: '0.000223037878108427'
            quote_token_balance: '64636039.082111'
            quote_token_liquidity_usd: '64494052.04397222'
            base_token_price_quote_token: '4483.543371561'
            quote_token_price_base_token: '0.0002230378781'
            address: '0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640'
            name: WETH / USDC 0.05%
            pool_name: WETH / USDC
            pool_fee_percentage: '0.05'
            pool_created_at: '2021-12-29T12:35:14Z'
            fdv_usd: '11190873336.847'
            market_cap_usd: '11195941219.2312'
            price_change_percentage:
              m5: '0'
              m15: '0.01'
              m30: '0'
              h1: '0'
              h6: '-0.31'
              h24: '0.06'
            transactions:
              m5:
                buys: 0
                sells: 4
                buyers: 0
                sellers: 4
              m15:
                buys: 7
                sells: 14
                buyers: 7
                sellers: 13
              m30:
                buys: 36
                sells: 36
                buyers: 30
                sellers: 31
              h1:
                buys: 72
                sells: 66
                buyers: 52
                sellers: 55
              h6:
                buys: 394
                sells: 374
                buyers: 270
                sellers: 306
              h24:
                buys: 1405
                sells: 1769
                buyers: 720
                sellers: 1312
            volume_usd:
              m5: '14474.0609971508'
              m15: '97230.627441051'
              m30: '217572.719149789'
              h1: '398012.377874174'
              h6: '2624801.54967643'
              h24: '14524209.5484025'
            net_buy_volume_usd:
              m5: '-14474.0609971508'
              m15: '20088.5420905036'
              m30: '112265.1687880188'
              h1: '213181.8440453441'
              h6: '39055.74647786'
              h24: '-3562.19491886'
            buy_volume_usd:
              m5: '0.0'
              m15: '58659.5847657773'
              m30: '164918.943968904'
              h1: '305597.110959759'
              h6: '1331928.64807714'
              h24: '7260323.6767418'
            sell_volume_usd:
              m5: '14474.0609971508'
              m15: '38571.0426752737'
              m30: '52653.7751808852'
              h1: '92415.2669144149'
              h6: '1292872.90159928'
              h24: '7263885.87166066'
            reserve_in_usd: '90053526.8909'
            locked_liquidity_percentage: '0.0'
          relationships:
            base_token:
              data:
                id: eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
                type: token
            quote_token:
              data:
                id: eth_0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
                type: token
            dex:
              data:
                id: uniswap_v3
                type: dex
        included:
          - id: eth_0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2
            type: token
            attributes:
              address: '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
              name: Wrapped Ether
              symbol: WETH
              decimals: 18
              image_url: >-
                https://coin-images.coingecko.com/coins/images/2518/large/weth.png?1696503332
              coingecko_coin_id: weth
    PoolData:
      type: object
      properties:
        id:
          type: string
        type:
          type: string
        attributes:
          type: object
          properties:
            base_token_price_usd:
              type: string
            base_token_price_native_currency:
              type: string
            base_token_balance:
              type: string
            base_token_liquidity_usd:
              type: string
            quote_token_price_usd:
              type: string
            quote_token_price_native_currency:
              type: string
            quote_token_balance:
              type: string
            quote_token_liquidity_usd:
              type: string
            base_token_price_quote_token:
              type: string
            quote_token_price_base_token:
              type: string
            address:
              type: string
            name:
              type: string
            pool_name:
              type: string
            pool_fee_percentage:
              type: string
            pool_created_at:
              type: string
            fdv_usd:
              type: string
            market_cap_usd:
              type: string
            price_change_percentage:
              type: object
              properties:
                m5:
                  type: string
                m15:
                  type: string
                m30:
                  type: string
                h1:
                  type: string
                h6:
                  type: string
                h24:
                  type: string
            transactions:
              type: object
              properties:
                m5:
                  type: object
                  properties:
                    buys:
                      type: integer
                    sells:
                      type: integer
                    buyers:
                      type: integer
                    sellers:
                      type: integer
                m15:
                  type: object
                  properties:
                    buys:
                      type: integer
                    sells:
                      type: integer
                    buyers:
                      type: integer
                    sellers:
                      type: integer
                m30:
                  type: object
                  properties:
                    buys:
                      type: integer
                    sells:
                      type: integer
                    buyers:
                      type: integer
                    sellers:
                      type: integer
                h1:
                  type: object
                  properties:
                    buys:
                      type: integer
                    sells:
                      type: integer
                    buyers:
                      type: integer
                    sellers:
                      type: integer
                h6:
                  type: object
                  properties:
                    buys:
                      type: integer
                    sells:
                      type: integer
                    buyers:
                      type: integer
                    sellers:
                      type: integer
                h24:
                  type: object
                  properties:
                    buys:
                      type: integer
                    sells:
                      type: integer
                    buyers:
                      type: integer
                    sellers:
                      type: integer
            volume_usd:
              type: object
              properties:
                m5:
                  type: string
                m15:
                  type: string
                m30:
                  type: string
                h1:
                  type: string
                h6:
                  type: string
                h24:
                  type: string
            net_buy_volume_usd:
              type: object
              properties:
                m5:
                  type: string
                m15:
                  type: string
                m30:
                  type: string
                h1:
                  type: string
                h6:
                  type: string
                h24:
                  type: string
            buy_volume_usd:
              type: object
              properties:
                m5:
                  type: string
                m15:
                  type: string
                m30:
                  type: string
                h1:
                  type: string
                h6:
                  type: string
                h24:
                  type: string
            sell_volume_usd:
              type: object
              properties:
                m5:
                  type: string
                m15:
                  type: string
                m30:
                  type: string
                h1:
                  type: string
                h6:
                  type: string
                h24:
                  type: string
            reserve_in_usd:
              type: string
            locked_liquidity_percentage:
              type: string
        relationships:
          type: object
          properties:
            base_token:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    id:
                      type: string
                    type:
                      type: string
            quote_token:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    id:
                      type: string
                    type:
                      type: string
            dex:
              type: object
              properties:
                data:
                  type: object
                  properties:
                    id:
                      type: string
                    type:
                      type: string
  securitySchemes:
    apiKeyAuth:
      type: apiKey
      in: header
      name: x-cg-demo-api-key
    apiKeyQueryParam:
      type: apiKey
      in: query
      name: x_cg_demo_api_key

````

Built with [Mintlify](https://mintlify.com).