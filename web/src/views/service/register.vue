<style scoped>
</style>
<template>
<Card>
    <Form ref="form" :model="form">
        <FormItem prop="Name" label="名称"><Input v-model="form.Name"/></FormItem>
        <FormItem prop="Command" label="命令行"><Input v-model="form.Command"/></FormItem>
        <FormItem prop="LogFile" label="日志文件"><Input v-model="form.LogFile"/></FormItem>
        <FormItem prop="Status" label="创建后立即启动"><Switch v-model="form.Status" disabled/></FormItem>
        <Button>创建服务</Button>
    </Form>
</Card>
</template>
<script>
export default {
    data () {
        return {
            form: {
                Name: "",
                Command: "",
                LogFile: "",
                Status: false
            }
        }
    }
}
</script>