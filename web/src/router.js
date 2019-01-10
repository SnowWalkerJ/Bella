const routers = [
    {
        path: '/config/contracts',
        meta: {
            title: '合约配置'
        },
        component: (resolve) => require(['./views/config/contracts.vue'], resolve)
    },
    {
        path: '/config/accounts',
        meta: {
            title: '账户配置'
        },
        component: (resolve) => require(['./views/config/accounts.vue'], resolve)
    },
    {
        path: '/service/monitor',
        meta: {
            title: '服务监控'
        },
        component: (resolve) => require(['./views/service/monitor.vue'], resolve)
    },
];
export default routers;