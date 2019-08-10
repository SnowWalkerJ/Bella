# Bella CTP 交易平台

Bella是一个CTP交易平台，包含了行情接收转存、拆单、管理交易等功能。
它由三部分组成：底层（行情）交易程序、Restful API、网页监控界面。

## 启动

Bella交易平台由多个服务组成，要正常发挥作用需要这些服务同时运行。

### MySQL

作为永久数据（如账号、订单等）的存储介质。

请安装MySQL数据库（也可以是其他数据库），并在`bella_rest/bella_rest/settings.py`中正确配置数据库连接信息。

安装方法：

```bash
apt install mysql
```

### Redis

作为零时数据（如价格、仓位）等的存储介质，以及通讯信息的传播载体。

请安装Redis数据库，并在`config.yml`中正确配置数据库连接信息。

安装方法：

```bash
apt install redis
```

### 安装bella模块

```bash
python setup.py install
```

### bella_rest

使用django搭建的restful API接口，封装了对数据库的读写。

```bash
cd bella_rest                      # 切换到bella_rest目录
python manage.py createsuperuser   # 创建管理员
vi bella_rest/settings.py          # 修改数据库连接信息和ALLOWED_HOSTS
gunicorn bella_rest.wsgi:application -b 0.0.0.0:6008  # 启动bella_rest服务
```

### 配置账号

浏览器打开`http://127.0.0.1:6008/admin`并使用创建的管理员账号登录，在`ctp_account`选项下新建CTP账号，并填写CTP连接信息

### 配置连接信息

编辑config.yml修改API的端口和Redis的连接信息

### 交易程序

```bash
python main/tradebot.py [ctp account]
```

### 行情程序

交易程序需要配合行情程序才能正确处理合约的最新价格。运行行情程序：

```bash
python main/market.py [ctp account]
```

## 程序示例

### 获取行情

参见`examples/market.py`

### 交易及获取仓位

参见`examples/trader.py`
