
import './assets/global-map-fix.css'
import 'flag-icons/css/flag-icons.min.css'
import 'vue-toast-notification/dist/theme-default.css'
import { createApp } from 'vue'
import ToastPlugin from 'vue-toast-notification'
import Shell from './Shell.vue'
import { i18n } from './i18n'
import router from './router'
import { mountWhenReady } from './bootstrap'

const app = createApp(Shell).use(ToastPlugin).use(i18n).use(router)
void mountWhenReady(router.isReady(), () => app.mount('#app'), (error) => {
  console.error('Application startup failed:', error)
  const notice = document.getElementById('startup-error')
  if (notice) notice.hidden = false
})
