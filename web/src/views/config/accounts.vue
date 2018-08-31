<style scoped>

</style>

<template>
<!-- TODO: validation -->
<div>
    <Row>
        <Col :span="12">
            <Card title="账号列表">
                <Table :columns="tableColumns" :data="accountsList" :loading="loading" @on-row-click="(row, index)=>{this.form=row}" highlight-row/>
            </Card>
        </Col>
        <Col :span="12">
            <Card>
                <Form ref="form" :label-width="90" :model="form">
                    <FormItem prop="Name" label="名称"><Input v-model="form.Name"/></FormItem>
                    <FormItem prop="UserID" label="用户代码"><Input v-model="form.UserID"/></FormItem>
                    <FormItem prop="Password" label="密码"><Input type="password" v-model="form.Password"/></FormItem>
                    <FormItem prop="BrokerID" label="经纪商代码"><Input v-model="form.BrokerID"/></FormItem>
                    
                    <FormItem prop="MdHost" label="行情服务器"><Input v-model="form.MdHost"/></FormItem>
                    <FormItem prop="TdHost" label="交易服务器"><Input v-model="form.TdHost"/></FormItem>
                    <FormItem prop="IsReal" label="是否实盘"><Checkbox v-model="form.IsReal"/></FormItem>
                    <div>
                        <Button size="large" @click="createAccount" type="primary">新增</Button>
                        <Button size="large">修改</Button>
                        <Button size="large" type="error">删除</Button>
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
            tableColumns: [
                {
                    key: "Name",
                    title: "名称",
                    sortable: true,
                },
                {
                    key: "UserID",
                    title: "用户ID",
                    sortable: true,
                },
                {
                    key: "IsReal",
                    title: "是否实盘",
                    sortable: true,
                    render: (h, params) => h('Icon', 
                        {props: {type: params.row.IsReal?'ios-checkbox-outline':'ios-square-outline'}}
                    )
                },
            ],
            accountsList: [
                {
                    Name: "Hello",
                    UserID: "042520",
                    Password: "",
                    BrokerID: "",
                    MdHost: "",
                    TdHost: "",
                    IsReal: false
                },
                {
                    Name: "Byebye",
                    UserID: "Byebye",
                    Password: "",
                    BrokerID: "",
                    MdHost: "",
                    TdHost: "",
                    IsReal: true
                }
            ],
            form: {
                Name: "",
                UserID: "",
                Password: "",
                BrokerID: "",
                MdHost: "",
                TdHost: "",
                IsReal: true
            }
        }
    },
    methods: {
        fetchData () {
            this.loading = true
            Util.ajax.get("/api/ctp/list").then(resp => {
                this.accountsList = resp.data
                this.loading = false
            })
        },
        createAccount () {
            Util.ajax.put("/api/ctp/create", this.form).then(resp => {
                this.form = {
                    Name: "",
                    UserID: "",
                    Password: "",
                    BrokerID: "",
                    MdHost: "",
                    TdHost: "",
                    IsReal: true
                }
                this.fetchData()
            })
        }
    },
    mounted () {
        this.fetchData()
    }
}
</script>
