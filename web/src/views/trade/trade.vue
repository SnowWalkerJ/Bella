<template>
<div>
    <div class="toolbox">
        <span>
            <Button>刷新</Button>
        </span>
        <span>
            <Button type= "primary" @click="manualTrade()">手工下单</Button>
        </span>
        <span>
            历史订单
            <i-switch v-model="showHistory" />
        </span>
        <span>
            已完成订单
            <i-switch v-model="showCompleted" />
        </span>
    </div>
    <Split v-model="splitValue" mode="vertical" :style="{height: '100%', minHeight: '500px'}">
        <Table :columns="orderColumns" :data="orderData" :highlight-row="true" :stripe="true" slot="top"/>
        <Table :columns="positionColumns" :data="positionData" :highlight-row="true" :stripe="true" slot="bottom"/>
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
                <Input v-model="tradeForm.Volume" placeholder="Volume" />
            </FormItem>
        </Form>
    </Modal>
</div>
</template>
<script>
import Util from '../../libs/util';
import strftime from 'strftime';
export default {
    data () {
        return {
            orderColumns: [
                {
                    key: 'ID',
                    title: 'ID',
                    type: 'index'
                },
                {
                    key: 'InstrumentID',
                    title: '合约',
                    sortable: true,
                },
                {
                    key: 'Direction',
                    title: '方向',
                    sortable: true,
                },
                {
                    key: 'Offset',
                    title: '开平',
                    sortable: true,
                },
                {
                    key: 'Price',
                    title: '价格'
                },
                {
                    key: 'Volume',
                    title: '数量'
                },
                {
                    key: 'Status',
                    title: '状态',
                    sortable: true,
                },
                {
                    key: 'InsertTime',
                    title: '发单时间',
                    sortable: true,
                },
                {
                    key: 'Operation',
                    title: '操作',
                    render: (h, params) => {
                        return h('Button', {
                            params: {
                                disabled: params.row.Status == "已完成",
                            },
                            on: {
                                click: () => {this.stop(params.row.ID);}
                            }
                        }, '停止');
                    }
                }
            ],
            orderData: [
                {
                    ID: 1,
                    InstrumentID: 'c1905',
                    Direction: '买入',
                    Offset: '开仓',
                    Price: '对手价',
                    InsertTime: '2019-03-21T14:23:40',
                    Status: '已完成',
                    Volume: '5/5'
                }
            ],
            positionColumns: [
                {
                    key: 'InstrumentID',
                    title: '合约',
                },
                {
                    key: 'NetAmount',
                    title: '净持仓',
                },
                {
                    key: 'TodayLAmount',
                    title: '今仓多头',
                },
                {
                    key: 'TodaySAmount',
                    title: '今仓空头',
                },
                {
                    key: 'YdLAmount',
                    title: '昨仓多头',
                },
                {
                    key: 'YdSAmount',
                    title: '昨仓空头',
                }
            ],
            positionData: [
                {
                    InstrumentID: 'c1905',
                    NetAmount: 36,
                    TodayLAmount: 36,
                    TodaySAmount: 0,
                    YdLAmount: 0,
                    YdSAmount: 0,
                }
            ],
            showCompleted: false,
            showHistory: false,
            showTradeModal: false,
            tradeForm: {
                InstrumentID: '',
                Direction: 0,
                Offset: 0,
                Price: 'CP',
                Volume: 1,
            },
            splitValue: 0.6
        };
    },
    methods: {
        manualTrade () {
            this.showTradeModal = true;
        },
        stop (ID) {
            alert(ID);
        },
        refreshOrders () {
            Util.ajax.request({
                url: "/api/order/",
                method: "GET",
                params: {}
            }).then(resp => {
                const data = resp.data;
                const date = new Data();
                let year = date.getFullYear(), month = date.getMonth(), day = date.getDate();
                const today = year + "-" + month + "-" + day;
                this.orderData.clear();
                for (let i = 0; i < data.Length; i++) {
                    const record = data[i];
                    if ((!this.showCompleted && record.Finished) || (!this.showHistory && today > record.InsertTime)) {
                        continue;
                    }
                    let myRecord = {
                        ID: record.ID,
                        InstrumentID: record.InstrumentID,
                        Direction: record.Direction === '0' ? '买入' : '卖出',
                        Offset: record.Offset === '0' ? '开仓' : '平仓',
                        Price: record.Price,
                        Volume: record.VolumesTraded + '/' + record.VolumesTotal,
                        Status: record.Finished ? '已完成' : '未完成',
                        InsertTime: record.InsertTime,
                    };
                    this.orderData.push(myRecord);
                }
            });
        },
        refreshPosition () {
            Util.ajax.request({
                url: "/api/position/",
                method: "GET",
                params: {}
            }).then((resp) => {

            });
        },
        interval_handler () {
            this.refreshOrders();
            this.refreshPosition();
        }
    },
    created () {
        this.timer = setInterval(this.interval_handler, 1000);
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

