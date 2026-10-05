<template>
  <div class="rp">
  <p class="rp-tip">
    提醒用于把记录成本压下来——该吃饭时想到记一餐，晨起空腹称一次体重。
  </p>

  <!-- 后台提醒：这是「页面关着也能响」的开关（Web Push，需 Service Worker 支持） -->
  <div class="rp-notify">
    <div class="rn-head">
      <span class="rn-ico"><AppIcon name="bell" :size="16" /></span>
      <div class="rn-t">
        <b>后台提醒</b>
        <span>{{ pushHint }}</span>
      </div>
      <button v-if="!pushOn && pushSupported" class="rn-btn" :disabled="pushBusy" @click="enablePush">
        开启
      </button>
      <span v-else class="rn-tag" :class="pushTagClass">{{ pushTag }}</span>
    </div>
    <div class="rn-actions" v-if="pushOn || pushSupported">
      <div class="rn-row">
        <button class="rn-ghost" :disabled="pushBusy || !pushOn" @click="testPush">发一条后台推送</button>
        <button v-if="pushOn" class="rn-ghost danger" :disabled="pushBusy" @click="disablePushNow">
          关闭后台提醒
        </button>
      </div>
      <span class="rn-note" v-if="!pushSupported">
        当前环境不支持后台推送（需要 HTTPS + 支持 Service Worker 的浏览器），页面打开时仍会提醒。
      </span>
      <span class="rn-note" v-else-if="pushPlan">
        到期即刻推送：{{ pushPlan }}
      </span>
    </div>
  </div>

  <!-- 通知通道：这是提醒能不能「真的弹出来」的开关 -->
  <div class="rp-notify">
    <div class="rn-head">
      <span class="rn-ico"><AppIcon name="bell" :size="16" /></span>
      <div class="rn-t">
        <b>系统通知</b>
        <span>{{ notifyHint }}</span>
      </div>
      <button v-if="permission === 'default'" class="rn-btn" @click="enableNotify">
        开启
      </button>
      <span v-else class="rn-tag" :class="permission">{{ notifyTag }}</span>
    </div>
    <div class="rn-actions">
      <button class="rn-ghost" @click="testNotify">发一条测试提醒</button>
      <span class="rn-note" v-if="permission === 'denied'">
        被浏览器拦截了：请点地址栏左侧的锁图标 → 网站设置 → 通知 → 允许，再刷新页面。
      </span>
    </div>
  </div>

  <div v-if="loading" class="rp-skeleton">
      <span class="sk-line" />
      <span class="sk-line short" />
    </div>

    <template v-else>
      <!-- 三餐 -->
      <div class="rp-card">
        <div class="rp-head">
          <div class="rp-t">
            <b>三餐提醒</b>
            <span>到点提示你记录当餐</span>
          </div>
          <van-switch v-model="form.meal_enabled" size="20px" :true-value="1" :false-value="0" />
        </div>
        <div v-if="form.meal_enabled" class="rp-body">
          <div class="rp-time" v-for="f in mealFields" :key="f.key">
            <span>{{ f.label }}</span>
            <input v-model="form[f.key]" type="time" class="time" />
          </div>
        </div>
      </div>

      <!-- 称重 -->
      <div class="rp-card">
        <div class="rp-head">
          <div class="rp-t">
            <b>称重提醒</b>
            <span>晨起空腹最稳定，建议固定时间</span>
          </div>
          <van-switch v-model="form.weigh_enabled" size="20px" :true-value="1" :false-value="0" />
        </div>
        <div v-if="form.weigh_enabled" class="rp-body">
          <div class="rp-time">
            <span>提醒时间</span>
            <input v-model="form.weigh_time" type="time" class="time" />
          </div>
        </div>
      </div>

      <!-- 饮水 -->
      <div class="rp-card">
        <div class="rp-head">
          <div class="rp-t">
            <b>饮水提醒</b>
            <span>按间隔在时段内提醒补水</span>
          </div>
          <van-switch v-model="form.water_enabled" size="20px" :true-value="1" :false-value="0" />
        </div>
        <div v-if="form.water_enabled" class="rp-body">
          <div class="rp-time">
            <span>开始</span>
            <input v-model="form.water_start" type="time" class="time" />
          </div>
          <div class="rp-time">
            <span>结束</span>
            <input v-model="form.water_end" type="time" class="time" />
          </div>
          <div class="rp-step">
            <span>提醒间隔</span>
            <div class="stepper">
              <button @click="stepInterval(-1)" :disabled="form.water_interval_hours <= 1">−</button>
              <b class="num">{{ form.water_interval_hours }} 小时</b>
              <button @click="stepInterval(1)" :disabled="form.water_interval_hours >= 6">+</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 免打扰 -->
      <div class="rp-card">
        <div class="rp-head">
          <div class="rp-t">
            <b>免打扰时段</b>
            <span>该时段内不发送任何提醒</span>
          </div>
          <van-switch v-model="form.quiet_enabled" size="20px" :true-value="1" :false-value="0" />
        </div>
        <div v-if="form.quiet_enabled" class="rp-body">
          <div class="rp-time">
            <span>开始</span>
            <input v-model="form.quiet_start" type="time" class="time" />
          </div>
          <div class="rp-time">
            <span>结束</span>
            <input v-model="form.quiet_end" type="time" class="time" />
          </div>
          <p class="rp-note">跨零点时段（如 22:30–07:00）会自动按次日处理。</p>
        </div>
      </div>

      <button class="rp-save" :disabled="saving" @click="save">
        {{ saving ? '保存中…' : '保存提醒设置' }}
      </button>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { showToast } from 'vant'
import AppIcon from './icons/AppIcon.vue'
import { getReminders, updateReminders } from '@/api/data'
import { testPush as apiTestPush } from '@/api/push'
import {
  notifyPermission,
  requestNotifyPermission,
  sendTestReminder,
  refreshReminders
} from '@/utils/reminder'
import {
  pushSupported as checkPushSupported,
  enablePush as apiEnablePush,
  disablePush as apiDisablePush,
  pushStatus,
  getExistingSubscription
} from '@/utils/push'

const MEAL_FIELDS = [
  { key: 'breakfast_time', label: '早餐' },
  { key: 'lunch_time', label: '午餐' },
  { key: 'dinner_time', label: '晚餐' }
]
const mealFields = MEAL_FIELDS

const ALL_FIELDS = [
  'meal_enabled', 'breakfast_time', 'lunch_time', 'dinner_time',
  'weigh_enabled', 'weigh_time',
  'water_enabled', 'water_start', 'water_end', 'water_interval_hours',
  'quiet_enabled', 'quiet_start', 'quiet_end'
]

const form = reactive({
  meal_enabled: 1,
  breakfast_time: '08:00',
  lunch_time: '12:00',
  dinner_time: '18:30',
  weigh_enabled: 1,
  weigh_time: '07:30',
  water_enabled: 1,
  water_start: '09:00',
  water_end: '21:00',
  water_interval_hours: 2,
  quiet_enabled: 1,
  quiet_start: '22:30',
  quiet_end: '07:00'
})

const loading = ref(false)
const saving = ref(false)

// 通知通道状态：设置只决定「什么时候提醒」，这里决定「能不能弹出来」
const permission = ref(notifyPermission())
const notifyHint = computed(() => {
  switch (permission.value) {
    case 'granted':
      return '已开启：到点会弹出系统通知，页面在后台标签页也收得到。'
    case 'denied':
      return '已被浏览器拦截，只能看到应用内提示条。'
    case 'unsupported':
      return '当前浏览器不支持系统通知，将只用应用内提示条。'
    default:
      return '开启后，到点会弹出系统通知；不开也能收到应用内提示条。'
  }
})
const notifyTag = computed(() => {
  switch (permission.value) {
    case 'granted':
      return '已开启'
    case 'denied':
      return '已拦截'
    case 'unsupported':
      return '不支持'
    default:
      return '未开启'
  }
})

async function enableNotify() {
  permission.value = await requestNotifyPermission()
  if (permission.value === 'granted') {
    showToast({ type: 'success', message: '系统通知已开启' })
  } else if (permission.value === 'denied') {
    showToast({ type: 'fail', message: '浏览器已拒绝通知权限' })
  }
}

function testNotify() {
  sendTestReminder()
  showToast({ message: '已发出一条测试提醒' })
}

// 后台提醒（Web Push）状态
const pushSupported = checkPushSupported()
const pushBusy = ref(false)
const pushOn = ref(false)
const pushPlan = ref('')
const pushHint = computed(() => {
  if (!pushSupported) return '当前环境不支持：页面打开时仍会收到提醒。'
  if (pushOn.value) return '已开启：浏览器关闭后，到点仍会推送到设备通知中心。'
  return '开启后，即使关闭浏览器也会按下面的时间收到提醒。'
})
const pushTagClass = computed(() => (pushOn.value ? 'granted' : 'unsupported'))
const pushTag = computed(() => {
  if (!pushSupported) return '不支持'
  return pushOn.value ? '已开启' : '未开启'
})

async function refreshPushState() {
  if (!pushSupported) return
  try {
    const sub = await getExistingSubscription()
    pushOn.value = !!sub
    const st = await pushStatus()
    const plan = (st && st.plan_today) || []
    pushPlan.value = plan.length
      ? plan.map((p) => `${p.time} ${p.title.replace('该', '').replace('了', '')}`).join(' · ')
      : ''
  } catch (e) {
    /* 拉取失败不影响本地开关的可用性 */
  }
}

async function enablePush() {
  pushBusy.value = true
  try {
    const r = await apiEnablePush()
    if (r.ok) {
      pushOn.value = true
      showToast({ type: 'success', message: '后台提醒已开启' })
    } else if (r.reason === 'denied') {
      showToast({ type: 'fail', message: '通知权限被拒绝，请先允许系统通知' })
    } else {
      showToast({ type: 'fail', message: '开启失败，请稍后重试' })
    }
    await refreshPushState()
  } finally {
    pushBusy.value = false
  }
}

async function disablePushNow() {
  pushBusy.value = true
  try {
    await apiDisablePush()
    pushOn.value = false
    showToast({ message: '后台提醒已关闭（页面打开时仍会提醒）' })
  } finally {
    pushBusy.value = false
  }
}

async function testPush() {
  pushBusy.value = true
  try {
    const r = await apiTestPush({})
    showToast({ type: 'success', message: `测试推送已发出（${r.subscribed} 台设备）` })
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    pushBusy.value = false
  }
}

async function load() {
  loading.value = true
  try {
    const data = await getReminders()
    ALL_FIELDS.forEach((k) => {
      if (data[k] != null) form[k] = data[k]
    })
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    loading.value = false
  }
}

function stepInterval(d) {
  const next = form.water_interval_hours + d
  if (next < 1 || next > 6) return
  form.water_interval_hours = next
}

async function save() {
  saving.value = true
  try {
    const payload = {}
    ALL_FIELDS.forEach((k) => {
      payload[k] = form[k]
    })
    const data = await updateReminders(payload)
    ALL_FIELDS.forEach((k) => {
      if (data[k] != null) form[k] = data[k]
    })
    showToast({ type: 'success', message: '已保存提醒设置' })
    // 让新时间立刻生效，不必等调度器的下一轮同步
    refreshReminders()
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await load()
  refreshPushState()
})
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.rp {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.rp-tip {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-2);
}

// 通知通道卡：提醒功能是否「真的能弹出来」，由这一块决定
.rp-notify {
  border: 1px solid var(--border);
  border-radius: @r-md;
  background: var(--surface);
  overflow: hidden;

  .rn-head {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 13px 14px;

    .rn-ico {
      width: 34px;
      height: 34px;
      flex-shrink: 0;
      border-radius: 11px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--lime-soft);
      color: var(--lime-ink);
    }
    .rn-t {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;

      b {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-1);
      }
      span {
        font-size: 11.5px;
        line-height: 1.55;
        color: var(--text-3);
      }
    }
  }

  .rn-btn {
    flex-shrink: 0;
    height: 32px;
    padding: 0 14px;
    border-radius: 999px;
    border: none;
    background: var(--lime);
    color: var(--on-lime);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
  .rn-tag {
    flex-shrink: 0;
    font-size: 11.5px;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--surface-2);
    color: var(--text-3);

    &.granted {
      background: var(--olive-soft);
      color: var(--olive);
    }
    &.denied,
    &.unsupported {
      background: var(--clay-soft);
      color: var(--clay);
    }
  }

  .rn-actions {
    padding: 10px 14px 13px;
    border-top: 1px solid var(--border);
    background: var(--surface-2);
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;

    .rn-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .rn-ghost {
      height: 34px;
      padding: 0 14px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text-2);
      font-size: 13px;
      cursor: pointer;

      &:hover:not(:disabled) {
        border-color: var(--lime-ink);
        color: var(--lime-ink);
      }
      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      &.danger:hover:not(:disabled) {
        border-color: var(--clay);
        color: var(--clay);
      }
    }
    .rn-note {
      font-size: 11.5px;
      line-height: 1.6;
      color: var(--clay);
    }
  }
}

.rp-card {
  border: 1px solid var(--border);
  border-radius: @r-md;
  overflow: hidden;
  background: var(--surface);
}

.rp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 14px;

  .rp-t {
    display: flex;
    flex-direction: column;
    gap: 2px;

    b {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-1);
    }
    span {
      font-size: 11.5px;
      color: var(--text-3);
    }
  }
}

.rp-body {
  padding: 12px 14px 14px;
  border-top: 1px solid var(--border);
  background: var(--surface-2);
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.rp-time {
  display: flex;
  align-items: center;
  justify-content: space-between;

  span {
    font-size: 13px;
    color: var(--text-2);
  }
}

.time {
  height: 36px;
  padding: 0 12px;
  border-radius: @r-sm;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-1);
  font-size: 14px;
  font-variant-numeric: tabular-nums;

  &:focus {
    outline: none;
    border-color: var(--lime-ink);
  }
}

.rp-step {
  display: flex;
  align-items: center;
  justify-content: space-between;

  > span {
    font-size: 13px;
    color: var(--text-2);
  }
  .stepper {
    display: flex;
    align-items: center;
    gap: 4px;

    button {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text-1);
      font-size: 17px;
      cursor: pointer;

      &:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
    }
    b {
      min-width: 68px;
      text-align: center;
      font-size: 13.5px;
      font-weight: 600;
      color: var(--text-1);
    }
  }
}

.rp-note {
  margin: 0;
  font-size: 11.5px;
  color: var(--text-3);
}

.rp-save {
  height: 46px;
  border-radius: 999px;
  border: none;
  background: var(--lime);
  color: var(--on-lime);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--glow-lime);

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.rp-skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;

  .sk-line {
    height: 14px;
    border-radius: 999px;
    background: var(--hover);
    animation: sk 1.2s @ease infinite;

    &.short {
      width: 60%;
    }
  }
}

@keyframes sk {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}
</style>
