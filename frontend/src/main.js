import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'
import './styles/global.less'
import { initTheme } from './store/modules/app'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Vant)

// 初始化深色模式（读取 localStorage 并写入 data-theme）
initTheme()

// 根字号由 global.less 的纯 CSS 控制：移动端 10vw 缩放，桌面锁定 37.5px，无需 JS 干预

app.mount('#app')

// PWA：仅在构建产物中注册 Service Worker。
// 开发态不注册——否则 vite 的热更新会被 SW 的缓存挡住，调试时看到的是旧代码。
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // 注册失败（如非 HTTPS、浏览器禁用）不影响主流程，静默降级为纯在线应用
    })
  })
}
