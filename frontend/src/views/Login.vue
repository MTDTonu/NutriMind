<template>
  <div class="auth-split">
    <!-- 品牌面板 -->
    <aside class="brand-panel">
      <div class="bp-top">
        <span class="bp-logo"><AppIcon name="logo" :size="20" /></span>
        <span class="bp-name">{{ brand.name }}</span>
        <span class="bp-badge num">{{ brand.nameEn }}</span>
      </div>

      <div class="bp-main">
        <span class="eyebrow">{{ brand.slogan }}</span>
        <h1 class="bp-headline">看懂你怎么吃<br /><span>再谈怎么瘦</span></h1>
        <p class="bp-sub">15 秒记完一餐 · 每周自动校准你的真实代谢</p>

        <div class="bp-metrics">
          <div class="bpm"><b class="num">15s</b><span>记完一餐</span></div>
          <div class="bpm"><b class="num">220+</b><span>内置中餐</span></div>
          <div class="bpm"><b class="num">TDEE</b><span>自适应校准</span></div>
        </div>
      </div>

      <div class="bp-foot num">© 2026 {{ brand.full }} · {{ brand.tagline }}</div>
    </aside>

    <!-- 表单面板 -->
    <main class="form-panel">
      <div class="form-box">
        <div class="fb-head">
          <span class="eyebrow">登录</span>
          <h2 class="fb-title">欢迎回来</h2>
          <p class="fb-sub">继续记录，让每一餐都被算清楚</p>
        </div>

        <!-- 演示账号提示：默认已填充，点一下即可进入 -->
        <div class="demo-tip">
          <AppIcon name="info" :size="15" />
          <span>
            演示账号 <b class="mono">demo / demo1234</b> 已自动填充，直接点「登录」即可
          </span>
        </div>

        <van-form class="form" @submit="onSubmit">
          <van-cell-group inset>
            <van-field
              v-model="form.username"
              name="username"
              label="用户名"
              autocomplete="username"
              placeholder="请输入用户名(4-20位)"
              :rules="[{ required: true, message: '请填写用户名' }, { validator: validateUsername, message: '用户名需 4-20 位' }]"
            />
            <van-field
              v-model="form.password"
              type="password"
              name="password"
              label="密码"
              autocomplete="current-password"
              placeholder="请输入密码(6-20位)"
              :rules="[{ required: true, message: '请填写密码' }, { validator: validatePassword, message: '密码需 6-20 位' }]"
            />
          </van-cell-group>

          <!-- 保持登录：勾选后 Token 过期会自动静默重登，等于长期在线 -->
          <label class="remember">
            <van-switch v-model="remember" size="19px" />
            <span class="rm-text">
              <b>保持登录状态</b>
              <i>关闭浏览器或重启服务后仍自动进入</i>
            </span>
          </label>

          <div class="submit">
            <van-button round block type="primary" native-type="submit" :loading="loading" loading-text="登录中...">
              {{ autoLogin ? '自动登录中' : '登 录' }}
            </van-button>
          </div>
        </van-form>

        <div class="footer">
          <span>还没有账号？</span>
          <span class="link" @click="goRegister">立即注册</span>
        </div>

        <div v-if="saved" class="forget">
          <span class="link-danger" @click="forgetSaved">清除本机已保存的账号</span>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import { useUserStore } from '@/store/modules/user'
import { showToast, showConfirmDialog } from 'vant'
import { DEMO_ACCOUNT, hasCredentials, clearCredentials } from '@/utils/credentials'
import { getToken } from '@/utils/auth'
import { BRAND as brand } from '@/config/brand'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
// 保持登录：默认开启。Token 过期时会用记住的凭据静默重登，等价于长期在线
const remember = ref(true)
// 本机是否已记住过账号（用于显示「清除」入口）
const saved = ref(hasCredentials())
const autoLogin = ref(false)

// 默认填充演示账号
const form = reactive({
  username: DEMO_ACCOUNT.username,
  password: DEMO_ACCOUNT.password
})

function validateUsername(val) {
  return val.length >= 4 && val.length <= 20
}
function validatePassword(val) {
  return val.length >= 6 && val.length <= 20
}

async function onSubmit() {
  if (loading.value) return
  loading.value = true
  try {
    await userStore.login({
      username: form.username.trim(),
      password: form.password,
      remember: remember.value
    })
    saved.value = hasCredentials()
    showToast({ type: 'success', message: remember.value ? '登录成功，已保持登录' : '登录成功' })
    if (userStore.isProfileComplete) {
      router.replace('/home')
    } else {
      router.replace('/profile-init')
    }
  } catch (e) {
    // 拦截器已提示
  } finally {
    loading.value = false
    autoLogin.value = false
  }
}

function goRegister() {
  router.push('/register')
}

async function forgetSaved() {
  try {
    await showConfirmDialog({
      title: '清除已保存的账号',
      message: '清除后下次打开需要重新输入账号密码。确定继续？'
    })
  } catch (e) {
    return
  }
  clearCredentials()
  saved.value = false
  showToast({ type: 'success', message: '已清除本机保存的账号' })
}

onMounted(() => {
  // 兜底：路由守卫正常情况下已经静默重登并直接跳转，这里只处理守卫未覆盖的场景
  // （如直接以 /login 进入、或 Token 恰好在守卫之后过期）
  if (!getToken() && hasCredentials()) {
    autoLogin.value = true
    onSubmit()
  }
})
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.auth-split {
  min-height: 100vh;
  display: flex;
}

// ---------- 品牌面板 ----------
.brand-panel {
  position: relative;
  width: 46%;
  max-width: 560px;
  padding: 40px 48px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  background: var(--bg-2);
  border-right: 1px solid var(--border);

  // 氛围：网格 + 青柠光斑
  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: linear-gradient(var(--grid-line) 1px, transparent 1px),
      linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
    background-size: 42px 42px;
    -webkit-mask-image: radial-gradient(90% 80% at 20% 10%, #000 40%, transparent 100%);
    mask-image: radial-gradient(90% 80% at 20% 10%, #000 40%, transparent 100%);
  }
  &::after {
    content: '';
    position: absolute;
    width: 520px;
    height: 520px;
    right: -180px;
    bottom: -200px;
    border-radius: 50%;
    background: radial-gradient(circle, var(--lime-soft), transparent 62%);
    filter: blur(20px);
  }

  .bp-top {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 10px;

    .bp-logo {
      width: 32px;
      height: 32px;
      border-radius: @r-md;
      background: var(--lime);
      color: var(--on-lime);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: var(--glow-lime);
    }
    .bp-name {
      font-family: @font-display;
      font-size: 17px;
      font-weight: 700;
      color: var(--text-1);
    }
    .bp-badge {
      font-size: 10px;
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid var(--border-2);
      color: var(--text-3);
    }
  }

  .bp-main {
    position: relative;
    z-index: 1;

    .bp-headline {
      font-family: @font-display;
      font-size: 52px;
      line-height: 1.02;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin: 18px 0 14px;
      color: var(--text-1);

      span {
        color: var(--lime-ink);
      }
    }
    .bp-sub {
      font-size: 14px;
      color: var(--text-3);
      letter-spacing: 0.04em;
      margin: 0;
    }
    .bp-metrics {
      margin-top: 34px;
      display: flex;
      gap: 26px;

      .bpm {
        display: flex;
        flex-direction: column;
        gap: 2px;
        b {
          font-size: 24px;
          font-weight: 800;
          color: var(--text-1);
          line-height: 1;
        }
        span {
          font-size: 11.5px;
          color: var(--text-3);
        }
      }
    }
  }

  .bp-foot {
    position: relative;
    z-index: 1;
    font-size: 11px;
    letter-spacing: 0.14em;
    color: var(--text-3);
  }
}

// ---------- 表单面板 ----------
.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}

.form-box {
  width: 100%;
  max-width: 384px;
}

// 演示账号提示条
.demo-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 11px 13px;
  margin-bottom: 18px;
  border-radius: @r-md;
  background: var(--lime-soft);
  border: 1px solid var(--border-2);
  color: var(--text-1);
  font-size: 12.5px;
  line-height: 1.55;

  span {
    flex: 1;
  }
  b.mono {
    font-family: @font-mono;
    color: var(--lime-ink);
    font-weight: 700;
  }
}

// 保持登录开关行
.remember {
  display: flex;
  align-items: center;
  gap: 11px;
  margin: 2px 0 16px;
  padding: 11px 13px;
  border-radius: @r-md;
  border: 1px solid var(--border);
  background: var(--surface-2);
  cursor: pointer;

  .rm-text {
    display: flex;
    flex-direction: column;
    gap: 1px;
    line-height: 1.35;

    b {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-1);
    }
    i {
      font-style: normal;
      font-size: 11.5px;
      color: var(--text-3);
    }
  }
}

.forget {
  text-align: center;
  margin-top: 10px;
  font-size: 12px;

  .link-danger {
    color: var(--text-3);
    cursor: pointer;
    &:hover {
      color: var(--red);
    }
  }
}

.fb-head {
  margin-bottom: 26px;

  .fb-title {
    font-family: @font-display;
    font-size: 30px;
    font-weight: 700;
    color: var(--text-1);
    margin: 12px 0 6px;
    letter-spacing: -0.01em;
  }
  .fb-sub {
    font-size: 13.5px;
    color: var(--text-3);
    margin: 0;
  }
}

.form {
  :deep(.van-field) {
    padding: 13px 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: @r-md;
    margin-bottom: 12px;
  }
  :deep(.van-cell-group--inset) {
    margin: 0;
    background: transparent;
    border-radius: 0;
  }
  :deep(.van-field__label) {
    width: 62px;
    color: var(--text-2);
  }
}

.submit {
  margin-top: 6px;
}

.footer {
  text-align: center;
  margin-top: 20px;
  color: var(--text-3);
  font-size: 13px;

  .link {
    color: var(--lime-ink);
    font-weight: 600;
    cursor: pointer;
    margin-left: 4px;
  }
}

// ---------- 移动端：品牌面板折叠为顶部横幅 ----------
@media (max-width: 900px) {
  .auth-split {
    flex-direction: column;
  }
  .brand-panel {
    width: 100%;
    max-width: none;
    padding: 22px 22px 26px;
    border-right: none;
    border-bottom: 1px solid var(--border);

    .bp-main .bp-headline {
      font-size: 34px;
      margin: 12px 0 8px;
    }
    .bp-metrics,
    .bp-foot {
      display: none;
    }
  }
  .form-panel {
    padding: 26px 20px 40px;
    align-items: flex-start;
  }
}
</style>
