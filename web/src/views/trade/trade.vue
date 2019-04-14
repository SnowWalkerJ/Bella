<template>
<div>
    <div class="toolbox">
        <span>
            <Select v-model="selectedAccount" style="width:200px">
                <Option v-for="account in this.accounts" :value="account" :key="account" :label="account" />
            </Select>
        </span>
        <span>
            <Button>刷新</Button>
        </span>
        <span>
            <Button type= "primary" @click="manualTrade()">手工下单</Button>
        </span>
    </div>
    <Split v-model="splitValue" ref="tables" mode="vertical" :style="{minHeight: this.height + 'px'}">
        <Table :columns="orderColumns" ref="orderTable" :height="orderHeight" :data="orderData" :highlight-row="true" :stripe="true" :border="true" slot="top"/>
        <Table :columns="positionColumns" ref="positionTable" :height="positionHeight" :data="positionData" :highlight-row="true" :stripe="true" :border="true" slot="bottom"/>
    </Split>
    <Modal v-model="showTradeModal" title="手动交易">
        <Form :model="tradeForm">
            <FormItem label="合约编号">
                <Input v-model="tradeForm.InstrumentID" placeholder="InstrumentID" />
            </FormItem>
            <FormItem label="交易方向">
                <RadioGroup v-model="tradeForm.Direction" type="button">
                    <Radio label="0">买入</Radio>
                    <Radio label="1">卖出</Radio>
                </RadioGroup>
            </FormItem>
            <FormItem label="开平">
                <RadioGroup v-model="tradeForm.Offset" type="button">
                    <Radio label="0">开仓</Radio>
                    <Radio label="1">平仓</Radio>
                </RadioGroup>
            </FormItem>
            <FormItem label="价格">
                <Input v-model="tradeForm.Price" placeholder="Price" />
            </FormItem>
            <FormItem label="数量">
                <InputNumber v-model="tradeForm.Volume" :min="1" :step="1" />
            </FormItem>
            <FormItem label="发单后等待">
                <InputNumber v-model="tradeForm.SplitSleepAfterSubmit" :min="1" :step="1" />
            </FormItem>
            <FormItem label="撤单后等待">
                <InputNumber v-model="tradeForm.SplitSleepAfterCancel" :min="1" :step="1" />
            </FormItem>
            <FormItem label="拆单比例">
                <InputNumber v-model="tradeForm.SplitPercent" :min="1" :step="1" />
            </FormItem>
        </Form>
    </Modal>
</div>
</template>
<script>
import Util from '../../libs/util';

function padZero(num, digits) {
    num = num + '';
    while (num.length < digits) {
        num = '0' + num;
    }
    return num;
}

export default {
    data () {
        return {
            accounts: ['simnow'],
            selectedAccount: 'simnow',
            orderColumns: [
                {
                    key: 'ID',
                    title: 'ID',
                    align: 'center',
                    type: 'index',
                    indexMethod: row => row.ID,
                },
                {
                    key: 'InstrumentID',
                    title: '合约',
                    sortable: true,
                    align: 'center',
                },
                {
                    key: 'Direction',
                    title: '方向',
                    sortable: true,
                    align: 'center',
                },
                {
                    key: 'Offset',
                    title: '开平',
                    sortable: true,
                    align: 'center',
                },
                {
                    key: 'Price',
                    title: '价格',
                    align: 'center',
                },
                {
                    key: 'Volume',
                    title: '数量',
                    align: 'center',
                },
                {
                    key: 'StatusMsg',
                    title: '消息',
                    align: 'center',
                    minWidth: 120,
                    tooltip: true,
                },
                {
                    key: 'Status',
                    title: '状态',
                    align: 'center',
                    sortable: true,
                    filters: [
                        {
                            label: '只显示未完成订单',
                            value: 1
                        }
                    ],
                    filterMultiple: false,
                    filterMethod (value, row) {
                        if (value == 1) {
                            console.log(row);
                            return row.Status != '已完成';
                        }
                    }
                },
                {
                    key: 'InsertTime',
                    title: '发单时间',
                    sortable: true,
                    align: 'center',
                    minWidth: 50,
                    filters: [
                        {
                            label: '只显示当日订单',
                            value: 1
                        }
                    ],
                    filterMultiple: false,
                    filterMethod: (value, row) => {
                        if (value === 1) {
                            return this.today <= row.InsertTime;
                        }
                    }
                },
                {
                    key: 'Operation',
                    title: '操作',
                    align: 'center',
                    render: (h, params) => {
                        return h('Button', {
                            params: {
                                disabled: params.row.Status === "已完成",
                            },
                            on: {
                                click: () => {this.stop(params.row.ID);}
                            }
                        }, '停止');
                    }
                }
            ],
            orderData: [],
            positionColumns: [
                {
                    key: 'InstrumentID',
                    title: '合约',
                    align: 'center',
                },
                {
                    key: 'NetAmount',
                    title: '净持仓',
                    align: 'center',
                    render: (h, params) => {
                        let color;
                        if (params.row.NetAmount > 0) {
                            color = 'red';
                        } else if (params.row.NetAmount < 0) {
                            color = 'green';
                        } else {
                            color = 'black';
                        }
                        return h('div', {
                            style: {
                                color
                            },
                        }, params.row.NetAmount);
                    }
                },
                {
                    title: '多头持仓',
                    key: 'LPosition',
                    align: 'center',
                    children: [
                        {
                            key: 'TotalLPosition',
                            title: '总多仓',
                            align: 'center',
                        },
                        {
                            key: 'TodayLPosition',
                            title: '今多仓',
                            align: 'center',
                        },
                        {
                            key: 'TodayLOpen',
                            title: '今多开',
                            align: 'center',
                        },
                        {
                            key: 'TodayLClose',
                            title: '今多平',
                            align: 'center',
                        },
                        {
                            key: 'YdLPosition',
                            title: '昨多仓',
                            align: 'center',
                        },
                        {
                            key: 'YdLClose',
                            title: '昨多平',
                            align: 'center',
                        },
                    ]
                },
                {
                    title: '空头持仓',
                    key: 'SPosition',
                    align: 'center',
                    children: [
                        {
                            key: 'TotalSPosition',
                            title: '总空仓',
                            align: 'center',
                        },
                        {
                            key: 'TodaySPosition',
                            title: '今空仓',
                            align: 'center',
                        },
                        {
                            key: 'TodaySOpen',
                            title: '今空开',
                            align: 'center',
                        },
                        {
                            key: 'TodaySClose',
                            title: '今空平',
                            align: 'center',
                        },
                        {
                            key: 'YdSPosition',
                            title: '昨空仓',
                            align: 'center',
                        },
                        {
                            key: 'YdSClose',
                            title: '昨空平',
                            align: 'center',
                        },
                    ],
                },
            ],
            positionData: [],
            showTradeModal: false,
            tradeForm: {
                InstrumentID: '',
                Direction: 0,
                Offset: 0,
                Price: 'CP',
                Volume: 1,
                SplitSleepAfterSubmit: 4,
                SplitSleepAfterCancel: 2,
                SplitPercent: 0.3,
            },
            splitValue: 0.6
        };
    },
    computed: {
        today () {
            const date = new Date();
            let year = date.getFullYear(), month = padZero(date.getMonth() + 1, 2), day = padZero(date.getDate(), 2);
            const today = year + "-" + month + "-" + day;
            return today;
        },
        orderHeight () {
            if (this.$refs.positionTable === undefined)
                return this.height * this.splitValue;
            return Math.round(this.$refs.tables.$el.offsetHeight * this.splitValue);
        },
        positionHeight () {
            if (this.$refs.positionTable === undefined)
                return this.height * this.splitValue;
            return Math.round(this.$refs.tables.$el.offsetHeight * (1 - this.splitValue));
        },
        height () {
            const offset = 150;
            return window.innerHeight - offset;
            // if (this.splitValue > 0 && this.$refs.positionTable === undefined)
            //     return window.innerHeight - offset;
            // else
            //     return (this.$el.offsetHeight > window.innerHeight ? this.$el.offsetHeight : window.innerHeight) - offset;
        }
    },
    methods: {
        manualTrade () {
            this.showTradeModal = true;
        },
        stop (ID) {
            alert(ID);
        },
        refreshAccounts () {
            Util.ajax.request({
                url: "/api/ctp/",
                method: "GET",
                params: {}
            }).then(resp => {
                let accounts = [];
                for (let account of resp.data) {
                    accounts.push(account.Name);
                }
                this.accounts = accounts;
            });
        },
        refreshOrders () {
            Util.ajax.request({
                url: "/api/order/",
                method: "GET",
                params: {Account: this.selectedAccount}
            }).then(resp => {
                const data = resp.data;
                let tmpData = [];
                for (let i = 0; i < data.length; i++) {
                    const record = data[i];
                    let myRecord = {
                        ID: record.ID,
                        InstrumentID: record.InstrumentID,
                        Direction: record.Direction === '0' ? '买入' : '卖出',
                        Offset: record.Offset === '0' ? '开仓' : '平仓',
                        Price: record.Price,
                        Volume: record.VolumesTraded + '/' + record.VolumesTotal,
                        Status: record.Status === 2 ? '已完成' : '未完成',
                        InsertTime: record.InsertTime,
                        StatusMsg: record.StatusMsg,
                    };
                    tmpData.push(myRecord);
                }
                this.orderData = tmpData;
            });
        },
        refreshPosition () {
            console.log('/api/position/' + this.selectedAccount);
            Util.ajax.request({
                url: '/api/position/' + this.selectedAccount,
                method: "GET",
                params: {}
            }).then((resp) => {
                let tmpData = [];
                for (let key in resp.data) {
                    let record = resp.data[key];
                    record.InstrumentID = key;
                    tmpData.push(record);
                }
                this.positionData = tmpData;
            });
        },
        interval_handler () {
            this.refreshAccounts();
            this.refreshOrders();
            this.refreshPosition();
        },
        sendOrder () {
            const data = {
                Account: this.selectedAccount,
                InstrumentID: this.tradeForm.InstrumentID,
                Direction: this.tradeForm.Direction,
                Offset: this.tradeForm.Offset,
                Price: this.tradeForm.Price,
                VolumesTotal: this.tradeForm.Volume,
                VolumesTraded: 0,
                SplitSleepAfterSubmit: this.tradeForm.SplitSleepAfterSubmit,
                SplitSleepAfterCancel: this.tradeForm.SplitSleepAfterCancel,
                SplitPercent: this.tradeForm.SplitPercent,
                Status: 1,
            };
            Util.ajax.request({
                url: '/api/order',
                method: 'PUT',
                data
            }).then(resp => {});
        }
    },
    created () {
        this.timer = setInterval(this.interval_handler, 3000);
    },
    beforeDestroy() {
        clearInterval(this.timer);
    },
}
</script>
<style scoped>
.toolbox {
    margin: 5px;
}
</style>

