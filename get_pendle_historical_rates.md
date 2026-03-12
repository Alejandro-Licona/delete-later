we need to find the best performing PT and LP tokens from pendle from January 1 2026 to March 12 2026

To retrieve historical rates for PT and LP tokens, refer to the PricesController_ohlcv_v4 endpoint for historical OHLCV price data. Additionally, the MarketsController_marketHistoricalData_v2 endpoint provides historical market time-series data, including ptPrice, lpPrice, and various APY metrics.

PENDLE_BASE_URL is https://api-v2.pendle.finance/core/

PricesController_ohlcv_v4 endpoint:
```json
    "/v4/{chainId}/prices/{address}/ohlcv": {
      "get": {
        "description": "\nHistorical price data for PT / YT tokens / LP tokens. We do not support historical prices for **SY and non-Pendle tokens**.\n\nThe data is OHLCV data, returned in CSV format with open, high, low, close prices, and volume.\n\nIn the case of LP, volume data will be 0. To get the correct volume, use our [Get market time-series data by address](#tag/markets/get/v2/{chainId}/markets/{address}/historical-data) endpoint.\n\n\nReturns at most 1440 data points.\n\nThe cost for the endpoint is based on how many data points are returned. The calculation is: `ceil(number of data points / 300)`.\n\nAt 1440 data points (which is 2 months of data with an hourly interval, or 4 years with a daily interval), the cost will be 5 computing units.\n\n",
        "operationId": "PricesController_ohlcv_v4",
        "parameters": [
          {
            "name": "chainId",
            "required": true,
            "in": "path",
            "schema": {
              "type": "number"
            }
          },
          {
            "name": "address",
            "required": true,
            "in": "path",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "time_frame",
            "required": false,
            "in": "query",
            "description": "Time interval for OHLCV data aggregation. Valid values: `hour`, `day`, `week`.",
            "schema": {
              "default": "hour",
              "enum": [
                "hour",
                "day",
                "week"
              ],
              "type": "string"
            }
          },
          {
            "name": "timestamp_start",
            "required": false,
            "in": "query",
            "description": "ISO Date string of the start time you want to query",
            "schema": {
              "format": "date-time",
              "type": "string"
            }
          },
          {
            "name": "timestamp_end",
            "required": false,
            "in": "query",
            "description": "ISO Date string of the end time you want to query",
            "schema": {
              "format": "date-time",
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "OHLCV data in CSV format with time, open, high, low, close, volume.",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/PriceOHLCVCSVResponse"
                },
                "example": {
                  "total": 1,
                  "currency": "USD",
                  "timeFrame": "hour",
                  "timestamp_start": 1756245600,
                  "timestamp_end": 1756245600,
                  "results": "time,open,high,low,close,volume\n1756245600,42.4563,42.4563,42.4563,42.4563,0.0000"
                }
              }
            }
          }
        },
        "summary": "Get PT / YT / LP historical price by address",
        "tags": [
          "Assets"
        ],
        "x-computing-unit": "1+",
        "x-retail-api-rank": 6969
      }
    }
```

MarketsController_marketHistoricalData_v2 endpoint: 
```json
    "/v2/{chainId}/markets/{address}/historical-data": {
      "get": {
        "description": "\nReturns the time-series data for a given market. Useful to draw charts or do data analysis.\n\nThis endpoint supports field selection via the `fields` query parameter. \n\nTable below shows the available fields and their descriptions.\n\n| Field | Description |\n|-------|-------------|\n| timestamp | Timestamp in ISO format|\n| baseApy | APY including yield, swap fee and Pendle rewards without boosting|\n| impliedApy | Implied APY of market|\n| lastEpochVotes | Last epoch votes|\n| lpPrice | LP price in USD|\n| lpRewardApy | APY from LP reward tokens|\n| maxApy | APY when maximum boost is applied|\n| pendleApy | APY from Pendle rewards|\n| ptPrice | PT price in USD|\n| swapFeeApy | Swap fee APY for LP holders, without boosting|\n| syPrice | SY price in USD|\n| totalPt | Total PT in the market|\n| totalSupply | Total supply of the LP token|\n| totalSy | Total SY in the market|\n| totalTvl | Market total TVL (including floating PT that are not in the AMM) in USD|\n| tradingVolume | 24h trading volume in USD|\n| tvl | Market liquidity (TVL in the pool) in USD|\n| underlyingApy | APY of the underlying asset|\n| underlyingInterestApy | Annual percentage yield from the underlying asset interest|\n| underlyingRewardApy | Annual percentage yield from the underlying asset rewards|\n| voterApr | APY for voters (vePENDLE holders) from voting on this pool|\n| ytFloatingApy | Floating APY for YT holders (underlyingApy - impliedApy)|\n| ytPrice | YT price in USD|\n\n\nReturns at most 1440 data points.\n\nThe cost for the endpoint is based on how many data points are returned. The calculation is: `ceil(number of data points / 300)`.\n\nAt 1440 data points (which is 2 months of data with an hourly interval, or 4 years with a daily interval), the cost will be 5 computing units.\n\n",
        "operationId": "MarketsController_marketHistoricalData_v2",
        "parameters": [
          {
            "name": "chainId",
            "required": true,
            "in": "path",
            "schema": {
              "type": "number"
            }
          },
          {
            "name": "address",
            "required": true,
            "in": "path",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "time_frame",
            "required": false,
            "in": "query",
            "schema": {
              "default": "hour",
              "enum": [
                "hour",
                "day",
                "week"
              ],
              "type": "string"
            }
          },
          {
            "name": "timestamp_start",
            "required": false,
            "in": "query",
            "schema": {
              "format": "date-time",
              "type": "string"
            }
          },
          {
            "name": "timestamp_end",
            "required": false,
            "in": "query",
            "schema": {
              "format": "date-time",
              "type": "string"
            }
          },
          {
            "name": "fields",
            "required": false,
            "in": "query",
            "description": "Comma-separated list of fields to include in the response. Use `all` to include all fields. Available fields could be found in the table above. \n\nAlthough you could use `all` to include all fields, it is not recommended because the bigger the payload is, the slower the response will be.",
            "schema": {
              "default": "underlyingApy,impliedApy,maxApy,baseApy,tvl",
              "example": "timestamp,maxApy,baseApy,underlyingApy,impliedApy,tvl,totalTvl,underlyingInterestApy,underlyingRewardApy,ytFloatingApy,swapFeeApy,voterApr,pendleApy,lpRewardApy,totalPt,totalSy,totalSupply,ptPrice,ytPrice,syPrice,lpPrice,lastEpochVotes,tradingVolume",
              "type": "string"
            }
          },
          {
            "name": "includeFeeBreakdown",
            "required": false,
            "in": "query",
            "description": "Whether you want to fetch fee breakdown data. Default is false. If enable, the response will include 3 fields: explicitSwapFee, implicitSwapFee, limitOrderFee and computing unit cost will be doubled. \n\nFee breakdown is only available for daily and weekly timeframes.",
            "schema": {
              "type": "boolean"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Historical data for the market",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/MarketHistoricalDataResponse"
                }
              }
            }
          }
        },
        "summary": "Get market time-series data by address",
        "tags": [
          "Markets"
        ],
        "x-computing-unit": "1+",
        "x-retail-api-rank": 3
      }
    }
```
