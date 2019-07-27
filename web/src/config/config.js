import Env from './env';

let config = {
    env: Env,
    ajaxUrl: Env === 'development' ? "http://127.0.0.1:8080/" : "http://snowwalkerj.cn:6008/"
};
export default config;