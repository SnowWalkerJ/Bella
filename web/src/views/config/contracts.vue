<style scoped>

</style>

<template>
<!-- TODO: validation -->
<div>
    <Row>
        <Col :span="12">
            <Card title="期货列表">
                <div><Tooltip content="支持正则表达式"><Input v-model="nameFilter" search placeholder="根据期货名称或代码过滤" icon="search" style="width: 300px"/></Tooltip></div>
                <Table :columns="tableColumns" :data="futuresList" :loading="loading" @on-row-click="(row, index)=>{this.form=row}" highlight-row/>
            </Card>
        </Col>
        <Col :span="12">
            <Card>
                <Form ref="form" :label-width="90" :model="form">
                    <FormItem prop="name" label="名称"><Input v-model="form.name"/></FormItem>
                    <FormItem prop="code" label="代码"><Input v-model="form.code"/></FormItem>
                    <FormItem prop="exchange" label="交易所"><Input v-model="form.exchange"/></FormItem>
                    <FormItem number prop="margin" label="保证金"><Input v-model="form.margin"/></FormItem>
                    <FormItem number prop="rateFee" label="比例交易费"><Input v-model="form.rateFee"/></FormItem>
                    <FormItem number prop="fixFee" label="固定交易费"><Input v-model="form.fixFee"/></FormItem>
                    <FormItem number prop="priceTick" label="最小价格变化"><Input v-model="form.priceTick"/></FormItem>
                    <FormItem number prop="multiple" label="合约乘数"><Input v-model="form.multiple"/></FormItem>
                    <FormItem prop="periods" label="交易时间段">
                        <div><Button icon="ios-add" @click="form.periods.push(['', ''])"/>
                        </div>
                        <div v-for="period, i in form.periods" :key="i">
                            <TimePicker
                                transfer
                                v-model="form.periods[i]"
                                type="timerange"
                                format="HH:mm"
                                :steps="[1,15]"
                            />
                            <Button icon="ios-trash" @click="form.periods.splice(i, 1)"/>
                        </div>
                    </FormItem>
                    <div>
                        <Button size="large" type="primary" @click="this.create">新增</Button>
                        <Button size="large" @click="this.modify">修改</Button>
                        <Button size="large" @click="this.remove" type="error">删除</Button>
                    </div>
                </Form>
            </Card>
        </Col>
    </Row>
</div>
</template>

<script>
import Util from '../../libs/util'
export default {
    data () {
        return {
            loading: true,
            nameFilter: "",
            tableColumns: [
                {
                    key: "code",
                    title: "代码",
                    sortable: true,
                },
                {
                    key: "name",
                    title: "名称",
                    sortable: true,
                },
                {
                    key: "exchange",
                    title: "交易所",
                    filters: [
                        {
                            value: "上期所",
                            label: "上期所",
                        },
                        {
                            value: "郑商所",
                            label: "郑商所",
                        },
                        {
                            value: "大商所",
                            label: "大商所",
                        },
                        {
                            value: "中金所",
                            label: "中金所",
                        }
                    ],
                    filterMethod(value, row) {
                        return value == row.exchange
                    }
                }
            ],
            futuresList: [
                {
                    code: "rb",
                    name: "螺纹钢",
                    exchange: "上期所",
                    margin: 0.1,
                    rateFee: 0.0001,
                    fixFee: 0.0,
                    priceTick: 1,
                    multiple: 10,
                    periods: [
                        ["09:00", "11:30"]
                    ]
                }
            ],
            form: {
                name: "",
                code: "",
                exchange: "",
                margin: "",
                rateFee: "",
                fixFee: "",
                priceTick: "",
                multiple: "",
                periods: [
                ]
            }
        }
    },
    methods: {
        fetchData () {
            this.loading = true
            Util.ajax.get("/api/futures/list").then(resp=>{
                this.futuresList = resp.data
                this.loading = false
            })
        },
        create () {
            Util.ajax.put("/api/futures/create", this.form).then(resp => {
                this.$Notice.success({
                    title: "创建品种",
                    desc: "创建品种成功"
                })
                this.fetchData()
            }).catch(error=>{
                this.$Notice.error({
                    title: "创建品种失败",
                    desc: error.response.statusText
                })
            })
        },
        modify () {
            Util.ajax.post("/api/futures/modify", this.form).then(resp => {
                this.$Notice.success({
                    title: "修改品种",
                    desc: "修改品种成功"
                })
                this.fetchData()
            }).catch(error=>{
                this.$Notice.error({
                    title: "修改品种失败",
                    desc: error.response.statusText
                })
            })
        },
        remove () {
            Util.ajax.post("/api/futures/delete", {name: this.form.name}).then(resp => {
                this.$Notice.success({
                    title: "删除品种",
                    desc: "删除品种成功"
                })
                this.fetchData()
            }).catch(error=>{
                this.$Notice.error({
                    title: "删除品种失败",
                    desc: error.response.statusText
                })
            })
        }
    },
    mounted () {
        this.fetchData()
    }
}
</script>
