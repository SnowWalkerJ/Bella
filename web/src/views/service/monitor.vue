<style scoped>

</style>

<template>
<Layout>
    <Row>
        <Col :span="8">
            <Alert show-icon type="success">{{summary.numAlive}}<p slot="desc">正常运行</p></Alert>
        </Col>
        <Col :span="8">
            <Alert show-icon type="error">{{summary.numDown}}<p slot="desc">发生错误</p></Alert>
        </Col>
        <Col :span="8">
            <Alert show-icon type="warning">{{summary.numOff}}<p slot="desc">关闭状态</p></Alert>
        </Col>
    </Row>
    <Row>
        <Col :span="12">
            <Table :columns="columns" :data="data" :loading="loading" @on-row-click="selectRow" border highlight-row/>
        </Col>
        <Col :span="12">
            <Card>
                <Form ref="form" :model="form">
                    <FormItem prop="Name" label="名称"><Input v-model="form.Name"/></FormItem>
                    <FormItem prop="Command" label="命令行"><Input v-model="form.Command"/></FormItem>
                    <FormItem prop="LogFile" label="日志文件"><Input v-model="form.LogFile"/></FormItem>
                    <Button @click="this.addService">添加</Button>
                    <Button @click="this.modifyService">编辑</Button>
                </Form>
            </Card>
        </Col>
    </Row>
</Layout>
</template>

<script>
import Util from '../../libs/util'
export default {
    data () {
        return {
            loading: true,
            columns: [
                {
                    key: "Name",
                    title: "名称",
                    sortable: true,
                },
                {
                    key: "Status",
                    title: "状态",
                    sortable: true,
                },
                {
                    key: "Operations",
                    title: "操作",
                    minWidth: 50,
                    render: (h, params) => h('div', [
                        h('Button', {
                            props: {disabled: params.row.Status=="正常运行"},
                            on: {click: ()=>this.startService(params.row.Name)}
                            }, '启动'),
                        h('Button', {
                            props: {disabled: params.row.Status!="正常运行"},
                            on: {click: ()=>this.shutdownService(params.row.Name)}
                            }, '停止'),
                        h('Button', {
                            props: {disabled: params.row.Status!="正常运行"},
                            on:{click: ()=>this.rebootService(params.row.Name)}
                            }, '重启'),
                        h('Button', {
                            props: {disabled: params.row.Status=="正常运行",},
                            on: {click: ()=>this.deleteService(params.row.Name)}
                            }, '删除'),
                    ])
                }
            ],
            data: [],
            form: {
                Name: "",
                Command: "",
                LogFile: "",
                Status: false
            }
        }
    },
    computed: {
        summary () {
            let result = {
                numAlive: 0,
                numDown: 0,
                numOff: 0,
            }
            for (let i in this.data) {
                let service = this.data[i]
                console.log(service)
                if (service.Status === "正常运行") {
                    result.numAlive ++
                } else if (service.Status === "异常退出") {
                    result.numDown ++
                } else {
                    result.numOff ++
                }
            }
            return result
        },
    },
    methods: {
        fetchData () {
            this.loading = true
            Util.ajax.get("/api/services/list").then(resp=>{
                this.data = resp.data
                this.loading = false
            })
        },
        startService(name) {
            Util.ajax.request({
                url: "/api/services/start",
                method: "POST",
                params: {name}
            }).then(this.fetchData)
        },
        shutdownService(name) {
            Util.ajax.request({
                url: "/api/services/shutdown",
                method: "POST",
                params: {name}
            }).then(this.fetchData)
        },
        rebootService(name) {
            Util.ajax.request({
                url: "/api/services/reboot",
                method: "POST",
                params: {name}
            }).then(this.fetchData)
        },
        deleteService(name) {
            Util.ajax.request({
                url: "/api/services/delete",
                method: "POST",
                params: {name}
            }).then(this.fetchData)
        },
        selectRow (row) {
            this.form = row
        },
        addService () {
            Util.ajax.post("/api/services/create", this.form).then(() => {
                this.form = {
                    Name: "",
                    Command: "",
                    LogFile: "",
                    Status: false
                }
                this.fetchData()
                this.$Notice.success({
                    title: "添加服务成功"
                })
            }).catch(error => {
                this.$Notice.error({
                    title: "添加服务失败",
                    desc: error.response.statusText
                })
            })
        },
        modifyService () {
            Util.ajax.post("/api/services/modify", this.form).then(() => {
                this.form = {
                    Name: "",
                    Command: "",
                    LogFile: "",
                    Status: false
                }
                this.fetchData()
                this.$Notice.success({
                    title: "编辑服务成功"
                })
            }).catch(error => {
                this.$Notice.error({
                    title: "编辑服务失败",
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
