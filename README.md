# Bella CTP 交易平台

Bella是一个CTP交易平台，包含了行情接收转存、拆单、管理交易等功能。
它由三部分组成：底层（行情）交易程序、Restful API、网页监控界面。

## 环境变量

- BELLA_MONGO_HOST
  - mongodb host, default localhost
- BELLA_MONGO_PORT
  - mongodb port, default 27017
- BELLA_MONGO_USER
  - optional, mongodb username
- BELLA_MONGO_PASSWD
  - optional, mongodb password
- BELLA_TICKS_HOST
  - arctic host (mongodb) for tickstore, default localhost
- BELLA_TICKS_USER
  - optional, mongodb username
- BELLA_TICKS_PASSWD
  - optional, mongodb password
- BELLA_REDIS_HOST
  - redis host, default localhost
- BELLA_REDIS_PORT
  - redis port, default 6379
- BELLA_REDIS_DB
  - redis db, default 0
- BELLA_REDIS_PASSWD
  - redis password, default None
