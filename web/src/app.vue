<style scoped>
.layout{
    border: 1px solid #d7dde4;
    background: #f5f7f9;
    position: relative;
    border-radius: 4px;
    overflow: hidden;
}
.layout-logo{
    width: 100px;
    height: 30px;
    background: #5b6270;
    border-radius: 3px;
    float: left;
    position: relative;
    top: 15px;
    left: 20px;
}
.layout-nav{
    width: 420px;
    margin: 0 auto;
    margin-right: 20px;
}
.high{
    min-height: 100vh;
}
</style>
<template>
    <div class="layout">
        <Layout>
            <Header>
                <Menu mode="horizontal" theme="dark" active-name="1">
                    <div class="layout-logo"></div>
                    <div class="layout-nav">
                        <MenuItem name="1">
                            <Icon type="ios-navigate"></Icon>
                            Item 1
                        </MenuItem>
                        <MenuItem name="2">
                            <Icon type="ios-keypad"></Icon>
                            Item 2
                        </MenuItem>
                        <MenuItem name="3">
                            <Icon type="ios-analytics"></Icon>
                            Item 3
                        </MenuItem>
                        <MenuItem name="4">
                            <Icon type="ios-paper"></Icon>
                            Item 4
                        </MenuItem>
                    </div>
                </Menu>
            </Header>
            <Layout>
                <Sider hide-trigger :style="{background: '#fff'}">
                    <Menu class="high" active-name="monitor" theme="light" width="auto" :open-names="['service']">
                        <Submenu name="service">
                            <template slot="title">
                                <Icon type="ios-cloud"></Icon>
                                服务
                            </template>
                            <MenuItem to="/service/monitor" name="monitor"><Icon type="ios-speedometer"/>服务状态</MenuItem>
                            <MenuItem name="crontab"><Icon type="ios-time"/>定时任务</MenuItem>
                        </Submenu>
                        <Submenu name="strategy">
                            <template slot="title">
                                <Icon type="ios-analytics"></Icon>
                                策略
                            </template>
                            <MenuItem name="logs">策略日志</MenuItem>
                            <MenuItem name="pnl">策略收益</MenuItem>
                        </Submenu>
                        <Submenu name="config">
                            <template slot="title">
                                <Icon type="ios-cog"></Icon>
                                配置
                            </template>
                            <MenuItem to="/config/contracts" name="contracts"><Icon type="ios-paper"/>合约配置</MenuItem>
                            <MenuItem to="/config/accounts" name="accounts"><Icon type="ios-person"/>账户配置</MenuItem>
                            <MenuItem name="3-3">主力合约表</MenuItem>
                            <MenuItem name="3-4"><Icon type="ios-card"/>账户关联</MenuItem>
                            <MenuItem name="3-5">K线合成</MenuItem>
                            
                        </Submenu>
                    </Menu>
                </Sider>
                <Layout :style="{padding: '0 24px 24px'}">
                    <Content class="high" :style="{padding: '24px', background: '#fff'}">
                        <router-view/>
                    </Content>
                </Layout>
            </Layout>
        </Layout>
    </div>
</template>
<script>
    export default {
        
    }
</script>
