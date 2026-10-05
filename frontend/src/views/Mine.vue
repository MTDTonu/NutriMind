<template>
  <div class="page mine">
    <NavBar title="我的" />

    <div class="mine-grid">
    <!-- 左列：设置列表 -->
    <div class="col-a">
    <div class="settings">
      <button class="set-item" @click="openProfile">
        <span class="si-ico"><AppIcon name="user" :size="18" /></span>
        <span class="si-label">个人资料</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
      <button class="set-item" @click="openPref">
        <span class="si-ico"><AppIcon name="diet" :size="18" /></span>
        <span class="si-label">饮食偏好</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
      <button class="set-item" @click="showCalendar = true">
        <span class="si-ico"><AppIcon name="calendar" :size="18" /></span>
        <span class="si-label">打卡日历</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
      <button class="set-item" @click="showBadge = true">
        <span class="si-ico"><AppIcon name="medal" :size="18" /></span>
        <span class="si-label">成就徽章</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
      <button class="set-item" @click="showTarget = true">
        <span class="si-ico"><AppIcon name="target" :size="18" /></span>
        <span class="si-label">智能目标</span>
        <span class="si-hint num" v-if="targetKcal">{{ targetKcal }} kcal</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
      <button class="set-item" @click="showReminder = true">
        <span class="si-ico"><AppIcon name="bell" :size="18" /></span>
        <span class="si-label">提醒设置</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
      <button class="set-item" @click="showData = true">
        <span class="si-ico"><AppIcon name="refresh" :size="18" /></span>
        <span class="si-label">数据导入导出</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
      <button class="set-item" @click="openAISettings">
        <span class="si-ico"><AppIcon name="settings" :size="18" /></span>
        <span class="si-label">大模型配置</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
      <div class="set-item static">
        <span class="si-ico"><AppIcon :name="darkOn ? 'moon' : 'sun'" :size="18" /></span>
        <span class="si-label">深色模式</span>
        <van-switch v-model="darkOn" size="20px" />
      </div>
      <button class="set-item" @click="showAbout = true">
        <span class="si-ico"><AppIcon name="info" :size="18" /></span>
        <span class="si-label">关于知食</span>
        <AppIcon name="chevdown" :size="16" class="si-arrow" />
      </button>
    </div>

    <button class="logout-btn" @click="onLogout">
      <AppIcon name="logout" :size="18" /> 退出登录
    </button>
    </div>

    <!-- 右列：真实数据总览（桌面端常驻，不再塞进弹窗） -->
    <aside class="col-b">
      <!-- 目标方案：桌面端直接可读可改，不用点开弹窗 -->
      <section class="panel">
        <h3 class="panel-h">
          当前目标
          <span class="panel-sub num">每天执行的目标热量</span>
        </h3>
        <TargetPanel @saved="onTargetSaved" @loaded="onTargetLoaded" />
      </section>

      <section class="panel">
        <h3 class="panel-h">我的数据</h3>
        <div class="kv-grid">
          <div class="kv">
            <span class="kv-k">基础代谢 BMR</span>
            <span class="kv-v num">{{ metrics.bmr ?? '--' }}<i>kcal</i></span>
          </div>
          <div class="kv">
            <span class="kv-k">每日消耗 TDEE</span>
            <span class="kv-v num">{{ metrics.tdee ?? '--' }}<i>kcal</i></span>
          </div>
          <div class="kv">
            <span class="kv-k">推荐摄入</span>
            <span class="kv-v num">{{ metrics.recommend_calorie ?? '--' }}<i>kcal</i></span>
          </div>
          <div class="kv">
            <span class="kv-k">BMI</span>
            <span class="kv-v num">{{ metrics.bmi ?? '--' }}<i>{{ bmiText }}</i></span>
          </div>
        </div>
        <p class="panel-note">
          以上数值由你的身高 / 体重 / 年龄 / 活动水平实时计算得出，不填充任何模拟值。
        </p>
      </section>

      <section class="panel">
        <h3 class="panel-h">打卡记录</h3>
        <div class="stat-row">
          <div class="stat">
            <b class="num">{{ checkin.continuous_days }}</b>
            <span>连续打卡（天）</span>
          </div>
          <div class="stat">
            <b class="num">{{ checkin.total_days }}</b>
            <span>累计打卡（天）</span>
          </div>
        </div>
        <div class="ci-status" :class="{ on: checkin.checked_today }">
          <span class="dot" />
          {{ checkin.checked_today ? '今日已打卡' : '今日还未打卡' }}
        </div>
        <button class="panel-link" @click="showCalendar = true">查看打卡日历 →</button>
      </section>

      <section class="panel">
        <h3 class="panel-h">
          成就徽章
          <span class="panel-sub num">{{ unlockedCount }}/{{ badges.length }}</span>
        </h3>
        <div class="badge-grid">
          <div class="badge" v-for="b in badges" :key="b.name" :class="{ locked: !b.unlocked }">
            <span class="badge-ico"><AppIcon :name="b.icon" :size="22" /></span>
            <span class="badge-name">{{ b.name }}</span>
            <span class="badge-cond">{{ b.cond }}</span>
          </div>
        </div>
      </section>
    </aside>
    </div>

    <!-- 智能目标（与右列同一套组件，移动端从这里打开） -->
    <van-popup v-model:show="showTarget" position="bottom" round :style="{ maxHeight: '88vh' }">
      <div class="popup-wrap">
        <div class="popup-title">智能目标</div>
        <TargetPanel @saved="onTargetSaved" />
      </div>
    </van-popup>

    <!-- 提醒设置 -->
    <van-popup v-model:show="showReminder" position="bottom" round :style="{ maxHeight: '88vh' }">
      <div class="popup-wrap">
        <div class="popup-title">提醒设置</div>
        <ReminderPanel />
      </div>
    </van-popup>

    <!-- 数据导入导出 -->
    <van-popup v-model:show="showData" position="bottom" round :style="{ maxHeight: '88vh' }">
      <div class="popup-wrap">
        <div class="popup-title">数据导入导出</div>
        <DataManagePanel />
      </div>
    </van-popup>

    <!-- 个人资料弹窗 -->
    <van-popup v-model:show="showProfile" position="bottom" round>
      <div class="popup-wrap">
        <div class="popup-title">编辑资料</div>
        <van-form @submit="saveProfile">
          <van-cell-group inset>
            <van-field name="gender" label="性别">
              <template #input>
                <van-radio-group v-model="profileForm.gender" direction="horizontal">
                  <van-radio :name="1">男</van-radio>
                  <van-radio :name="0">女</van-radio>
                </van-radio-group>
              </template>
            </van-field>
            <van-field v-model="profileForm.age" type="digit" label="年龄" placeholder="岁" />
            <van-field v-model="profileForm.height" type="digit" label="身高(cm)" />
            <van-field v-model="profileForm.current_weight" type="digit" label="当前体重(kg)" />
            <van-field v-model="profileForm.target_weight" type="digit" label="目标体重(kg)" />
            <van-field name="activity_level" label="活动水平">
              <template #input>
                <van-radio-group v-model="profileForm.activity_level" direction="horizontal">
                  <van-radio :name="1">久坐</van-radio>
                  <van-radio :name="2">轻度</van-radio>
                  <van-radio :name="3">中度</van-radio>
                  <van-radio :name="4">高强度</van-radio>
                </van-radio-group>
              </template>
            </van-field>
          </van-cell-group>
          <div class="popup-actions">
            <van-button block round type="primary" native-type="submit">保存</van-button>
          </div>
        </van-form>
      </div>
    </van-popup>

    <!-- 饮食偏好弹窗 -->
    <van-popup v-model:show="showPref" position="bottom" round>
      <div class="popup-wrap">
        <div class="popup-title">饮食偏好</div>
        <div class="chips">
          <span
            v-for="p in prefOptions"
            :key="p"
            class="chip"
            :class="{ on: prefSel.includes(p) }"
            @click="togglePref(p)"
          >
            {{ p }}
          </span>
        </div>
        <van-field
          v-model="prefAvoid"
          type="textarea"
          label="忌口/过敏"
          placeholder="如：不吃香菜、海鲜过敏"
          rows="1"
          autosize
        />
        <div class="popup-actions">
          <van-button block round type="primary" @click="savePref">保存</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 成就徽章 -->
    <van-popup v-model:show="showBadge" position="bottom" round>
      <div class="popup-wrap">
        <div class="popup-title">成就徽章</div>
        <div class="badge-grid">
          <div class="badge" v-for="b in badges" :key="b.name" :class="{ locked: !b.unlocked }">
            <span class="badge-ico"><AppIcon :name="b.icon" :size="22" /></span>
            <span>{{ b.name }}</span>
          </div>
        </div>
      </div>
    </van-popup>

    <!-- 关于 -->
    <van-popup v-model:show="showAbout" position="bottom" round>
      <div class="popup-wrap">
        <div class="popup-title">关于{{ brand.full }}</div>
        <p class="about-text">
          {{ brand.full }} · {{ brand.tagline }} v{{ brand.version }}<br />
          基于 Vue 3 + FastAPI 构建：内置 {{ foodTotal || '220+' }} 条中餐食物库，
          用你的真实摄入与体重曲线反推代谢，每周自动校准目标热量，
          让一条餐食记录的成本压到 15 秒以内。
        </p>
      </div>
    </van-popup>

    <!-- 大模型配置：文字 / 视觉理解 / 语言转文字 三套独立配置 -->
    <!-- 只保留 .van-popup 一个滚动容器（Vant 内置 overflow-y:auto），
         避免与其内部再叠一层 max-height/overflow 形成双滚动条 -->
    <van-popup
      v-model:show="showAISet"
      position="bottom"
      round
      class="ai-popup"
      :style="{ maxHeight: '82vh' }"
    >
      <div class="popup-wrap ai-conf">
        <div class="popup-title">大模型配置</div>
        <p class="ai-conf-tip">
          分别为「文字 / 视觉理解 / 语言转文字」选择国内厂商与模型，可自由混搭。
          保存后自动同步至服务端并写回 <code>.env</code>。
        </p>

        <div class="cap-card" v-for="c in CAPS" :key="c.key">
          <div class="cap-head">
            <span class="cap-ico"><AppIcon :name="c.icon" :size="16" /></span>
            <div class="cap-t">
              <b>{{ c.title }}</b>
              <span>{{ c.desc }}</span>
            </div>
          </div>

          <div class="field-label">厂商</div>
          <div class="prov-chips">
            <button
              v-for="(label, p) in providerLabels"
              :key="p"
              class="prov-chip"
              :class="{ on: form[c.key].provider === p }"
              @click="pickProvider(c.key, p)"
            >
              {{ label }}
            </button>
          </div>

          <div class="field-label">
            API Key
            <span v-if="masked[c.key].has_key" class="key-hint">{{ masked[c.key].masked_key }} · 留空保持</span>
            <span v-else class="key-hint dim">未配置</span>
          </div>
          <input
            v-model="form[c.key].api_key"
            class="ai-input"
            type="password"
            :placeholder="masked[c.key].has_key ? '已配置，留空则保持不变' : '粘贴厂商 API Key'"
            autocomplete="off"
            spellcheck="false"
          />

          <div class="field-label">模型名</div>
          <input
            v-model="form[c.key].model"
            class="ai-input"
            :placeholder="defaultModelHint(c.key)"
            autocomplete="off"
            spellcheck="false"
          />

          <p class="cap-note free-note" v-if="freeModelsOf(c.key).length">
            <span class="ft-badge" v-if="isFreeModel(c.key)">免费</span>
            该厂商免费模型：{{ freeModelsOf(c.key).join(' / ') }}
          </p>

          <template v-if="form[c.key].provider === 'custom'">
            <div class="field-label">Base URL（OpenAI 兼容）</div>
            <input
              v-model="form[c.key].base_url"
              class="ai-input"
              placeholder="https://your-endpoint/v1"
              autocomplete="off"
              spellcheck="false"
            />
          </template>

          <p class="cap-note" v-if="c.key === 'asr'">
            当前语音输入使用浏览器内置识别（无需 Key）；此处配置预留给服务端 ASR 扩展。
          </p>
        </div>

        <div class="popup-actions">
          <van-button block round type="primary" :loading="savingAi" @click="saveAISettings">
            保存配置
          </van-button>
        </div>
      </div>
    </van-popup>

    <!-- 打卡日历：真实打卡日高亮（来自 user_checkin 表） -->
    <van-calendar
      v-model:show="showCalendar"
      :min-date="minDate"
      :max-date="maxDate"
      :show-confirm="false"
      :formatter="calendarFormatter"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import TargetPanel from '@/components/TargetPanel.vue'
import ReminderPanel from '@/components/ReminderPanel.vue'
import DataManagePanel from '@/components/DataManagePanel.vue'
import { useUserStore } from '@/store/modules/user'
import { useAppStore } from '@/store/modules/app'
import { updateProfile, updatePreference, getMetrics, getCheckin } from '@/api/auth'
import { weightTrend } from '@/api/stats'
import { getAISettings, updateAISettings, getAISettingsProviders } from '@/api/user'
import { searchFoods } from '@/api/food'
import { BRAND as brand } from '@/config/brand'
import { showToast, showLoadingToast, closeToast } from 'vant'

const router = useRouter()
const userStore = useUserStore()
// 内置食物库规模（用于「关于」弹窗，取不到则显示保守文案）
const foodTotal = ref(0)
const appStore = useAppStore()

// 用户信息统一展示在侧栏底部卡片（点击可进入「我的」），此处不再重复渲染
const user = computed(() => userStore.userInfo || {})

// 深色模式开关：必须绑定到 appStore 的响应式状态，而不能用 ref(appStore.isDark)
// 这种「一次性快照」（其它地方切主题时这里不会同步）。改用 computed 双向绑定。
const darkOn = computed({
  get: () => appStore.isDark,
  set: (v) => appStore.setDark(v)
})

// 弹窗控制
const showProfile = ref(false)
const showPref = ref(false)
const showBadge = ref(false)
const showAbout = ref(false)
const showCalendar = ref(false)
const showTarget = ref(false)
const showReminder = ref(false)
const showData = ref(false)
// 目标面板里保存后回填的目标热量，用于在设置项右侧显示
const targetKcal = ref('')

function onTargetLoaded(target) {
  if (target && target.target_calorie) targetKcal.value = Math.round(target.target_calorie)
}
function onTargetSaved(data) {
  if (data && data.target_calorie) targetKcal.value = Math.round(data.target_calorie)
}
const minDate = new Date(new Date().setMonth(new Date().getMonth() - 3))
const maxDate = new Date()

// 后端 ProfileUpdate 约定：gender 0 女 / 1 男，activity_level 1~4（int）
// 这里必须用数字，传字符串会被 pydantic 校验拦下 -> 400
const profileForm = reactive({
  gender: 0,
  age: '',
  height: '',
  current_weight: '',
  target_weight: '',
  activity_level: 2
})

function openProfile() {
  const u = user.value || {}
  Object.assign(profileForm, {
    // 注意：gender=0（女）是合法值，不能写成 `u.gender || 0` 之外的假值兜底
    gender: u.gender === 1 ? 1 : 0,
    age: u.age != null ? String(u.age) : '',
    height: u.height != null ? String(u.height) : '',
    current_weight: u.current_weight != null ? String(u.current_weight) : '',
    target_weight: u.target_weight != null ? String(u.target_weight) : '',
    activity_level: [1, 2, 3, 4].includes(Number(u.activity_level))
      ? Number(u.activity_level)
      : 2
  })
  showProfile.value = true
}

async function saveProfile() {
  try {
    const num = (v) => (v === '' || v === null || v === undefined ? undefined : Number(v))
    const payload = {
      gender: Number(profileForm.gender),
      age: num(profileForm.age),
      height: num(profileForm.height),
      current_weight: num(profileForm.current_weight),
      target_weight: num(profileForm.target_weight),
      activity_level: Number(profileForm.activity_level)
    }
    // 去掉未填写项，避免传 undefined 被 JSON 序列化成 null 触发校验失败
    Object.keys(payload).forEach((k) => {
      if (payload[k] === undefined || Number.isNaN(payload[k])) delete payload[k]
    })
    await updateProfile(payload)
    await userStore.fetchUserInfo()
    showToast({ type: 'success', message: '已保存' })
    showProfile.value = false
  } catch (e) {
    showToast({ type: 'fail', message: (e && e.message) || '保存失败' })
  }
}

const prefOptions = ['高蛋白', '低脂肪', '低碳水', '素食', '少油少盐', '清淡', '均衡']
const prefSel = ref([])
const prefAvoid = ref('')
function openPref() {
  prefSel.value = (user.value.diet_preference || '').split(',').filter(Boolean)
  prefAvoid.value = user.value.diet_avoid || ''
  showPref.value = true
}
function togglePref(p) {
  const i = prefSel.value.indexOf(p)
  if (i >= 0) prefSel.value.splice(i, 1)
  else prefSel.value.push(p)
}
async function savePref() {
  try {
    const diet_preference = prefSel.value.join(',')
    await updatePreference({ diet_preference, diet_avoid: prefAvoid.value })
    await userStore.fetchUserInfo()
    showToast({ type: 'success', message: '已保存' })
    showPref.value = false
  } catch (e) {}
}

/* ---------------- 真实数据（全部来自后端，无模拟值） ---------------- */
const metrics = ref({ bmr: null, tdee: null, recommend_calorie: null, bmi: null })
const checkin = ref({ continuous_days: 0, total_days: 0, checked_today: false, dates: [] })
const lostWeight = ref(0)

const bmiText = computed(() => {
  const v = Number(metrics.value.bmi)
  if (!v) return ''
  if (v < 18.5) return '偏瘦'
  if (v < 24) return '正常'
  if (v < 28) return '超重'
  return '肥胖'
})

// 徽章解锁条件全部基于真实数据判定
const badges = computed(() => [
  {
    name: '初次打卡',
    icon: 'target',
    cond: '累计打卡 ≥ 1 天',
    unlocked: checkin.value.total_days >= 1
  },
  {
    name: '连续 7 天',
    icon: 'fire',
    cond: '连续打卡 ≥ 7 天',
    unlocked: checkin.value.continuous_days >= 7
  },
  {
    name: '减脂 5kg',
    icon: 'medal',
    cond: '累计减重 ≥ 5kg',
    unlocked: lostWeight.value >= 5
  },
  {
    name: '达成目标',
    icon: 'star',
    cond: '当前体重 ≤ 目标体重',
    unlocked:
      !!user.value.current_weight &&
      !!user.value.target_weight &&
      Number(user.value.current_weight) <= Number(user.value.target_weight)
  }
])
const unlockedCount = computed(() => badges.value.filter((b) => b.unlocked).length)

// 日历：把真实打卡日标出来
function calendarFormatter(day) {
  const d = day.date
  const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate()
  ).padStart(2, '0')}`
  if (checkin.value.dates && checkin.value.dates.includes(key)) {
    day.type = 'success'
    day.bottomInfo = '已打卡'
  }
  return day
}

async function fetchCheckin() {
  try {
    const res = await getCheckin()
    if (res) {
      checkin.value = {
        continuous_days: Number(res.continuous_days) || 0,
        total_days: Number(res.total_days) || 0,
        checked_today: !!res.checked_today,
        dates: Array.isArray(res.dates) ? res.dates : []
      }
    }
  } catch (e) {
    /* 保持 0，不伪造 */
  }
}

function onLogout() {
  userStore.logout()
  router.replace('/login')
}

/* ---------------- 大模型配置（文字 / 视觉 / 语音 三套） ---------------- */
const showAISet = ref(false)
const savingAi = ref(false)
const providerLabels = ref({})
const providerDefaults = ref({})
const freeModels = ref({})

const CAPS = [
  { key: 'text', title: '文字生成', desc: '对话、食谱、每日复盘', icon: 'ai' },
  { key: 'vision', title: '视觉理解', desc: '拍照识别食物与热量', icon: 'camera' },
  { key: 'asr', title: '语言转文字', desc: '语音输入（浏览器端识别）', icon: 'chat' }
]

const form = reactive({
  text: { provider: 'zhipu', api_key: '', model: '', base_url: '' },
  vision: { provider: 'zhipu', api_key: '', model: '', base_url: '' },
  asr: { provider: 'zhipu', api_key: '', model: '', base_url: '' }
})
const masked = reactive({
  text: { has_key: false, masked_key: null },
  vision: { has_key: false, masked_key: null },
  asr: { has_key: false, masked_key: null }
})

async function ensureProviders() {
  if (Object.keys(providerLabels.value).length) return
  try {
    const meta = await getAISettingsProviders()
    providerLabels.value = meta.labels || {}
    providerDefaults.value = meta.defaults || {}
    freeModels.value = meta.free_models || {}
  } catch (e) {
    /* 读取失败则保留空，前端仅用内置兜底 */
  }
}

async function openAISettings() {
  showAISet.value = true
  await ensureProviders()
  try {
    const res = await getAISettings()
    for (const c of CAPS) {
      const s = (res && res[c.key]) || {}
      const prov = s.provider || 'zhipu'
      form[c.key].provider = prov
      // 未配置模型时预填该厂商的默认模型（智谱即免费 Flash 系列），保证开箱即用不产生费用
      form[c.key].model =
        s.model || (providerDefaults.value[prov] && providerDefaults.value[prov][c.key]) || ''
      form[c.key].base_url = s.base_url || ''
      form[c.key].api_key = '' // 不回填明文，留空表示保持原值
      masked[c.key].has_key = !!s.has_key
      masked[c.key].masked_key = s.masked_key || null
    }
  } catch (e) {
    showToast({ type: 'fail', message: '读取配置失败' })
  }
}

function pickProvider(capKey, p) {
  form[capKey].provider = p
  const def = (providerDefaults.value[p] && providerDefaults.value[p][capKey]) || ''
  if (p === 'custom') {
    // 自定义：清空默认模型，交由用户填写
    if (!form[capKey].model) form[capKey].model = ''
  } else if (def) {
    form[capKey].model = def
  }
}

function defaultModelHint(capKey) {
  const p = form[capKey].provider
  const def = providerDefaults.value[p] && providerDefaults.value[p][capKey]
  return def ? `默认：${def}` : '模型名（如 glm-4-flash）'
}

// 各厂商已确认免费的模型清单（由后端 /ai-settings/providers 下发）
function freeModelsOf(capKey) {
  const p = form[capKey].provider
  return freeModels.value[p] || []
}

// 当前填写的模型是否属于免费清单（用于显示「免费」徽标）
function isFreeModel(capKey) {
  const m = (form[capKey].model || '').trim()
  return !!m && freeModelsOf(capKey).includes(m)
}

async function saveAISettings() {
  savingAi.value = true
  try {
    const data = {}
    for (const c of CAPS) {
      const f = form[c.key]
      const item = { provider: f.provider }
      if (f.api_key && f.api_key.trim()) item.api_key = f.api_key.trim()
      if (f.model && f.model.trim()) item.model = f.model.trim()
      if (f.base_url && f.base_url.trim()) item.base_url = f.base_url.trim()
      data[c.key] = item
    }
    await updateAISettings(data)
    showToast({ type: 'success', message: '已保存并同步 .env' })
    showAISet.value = false
  } catch (e) {
    showToast({ type: 'fail', message: (e && e.message) || '保存失败' })
  } finally {
    savingAi.value = false
  }
}

onMounted(async () => {
  try {
    const res = await getMetrics()
    if (res) metrics.value = { ...metrics.value, ...res }
    if (res && res.bmi != null) userStore.updateUserInfo({ bmi: res.bmi })
  } catch (e) {
    /* 指标取不到就显示 --，不填假值 */
  }
  fetchCheckin()
  try {
    const f = await searchFoods({ limit: 1 })
    if (f && f.total) foodTotal.value = f.total
  } catch (e) {
    /* 数量取不到不影响其它功能 */
  }
  try {
    const t = await weightTrend({ range: 'month' })
    const ws = (t && t.weights) || []
    if (ws.length >= 2) {
      // 真实减重：区间最早记录 - 最新记录（正数代表下降）
      lostWeight.value = Math.max(0, Number((ws[0] - ws[ws.length - 1]).toFixed(1)))
    }
  } catch (e) {
    /* 无体重记录则为 0 */
  }
})
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.page.mine {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 720px;
  margin: 0 auto;
}

// 桌面端：双栏（左设置 / 右真实数据），不再是一条通栏的手机列表
@media (min-width: 1024px) {
  .page.mine {
    max-width: none;
  }
  .mine-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 0.85fr);
    gap: 20px;
    align-items: start;
  }
  .col-a,
  .col-b {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
  }
  .col-b {
    position: sticky;
    top: 0;
  }
}

/* ---------- 右侧面板 ---------- */
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: @r-lg;
  padding: 18px 18px 16px;

  .panel-h {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0 0 14px;
    font-family: @font-display;
    font-size: 14px;
    font-weight: 700;
    color: var(--text-2);
    letter-spacing: 0.04em;
  }
  .panel-sub {
    font-size: 12px;
    color: var(--text-3);
    font-weight: 600;
  }
  .panel-note {
    margin: 12px 0 0;
    font-size: 11.5px;
    line-height: 1.6;
    color: var(--text-3);
  }
}

.kv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;

  .kv {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: @r-md;
    padding: 11px 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }
  .kv-k {
    font-size: 11.5px;
    color: var(--text-3);
  }
  .kv-v {
    font-family: @font-mono;
    font-size: 17px;
    font-weight: 700;
    color: var(--text-1);
    display: flex;
    align-items: baseline;
    gap: 3px;

    i {
      font-style: normal;
      font-size: 11px;
      font-weight: 400;
      color: var(--text-3);
    }
  }
}

.stat-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;

  .stat {
    background: var(--lime-soft);
    border-radius: @r-md;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;

    b {
      font-family: @font-mono;
      font-size: 24px;
      font-weight: 700;
      color: var(--lime-ink);
      line-height: 1.1;
    }
    span {
      font-size: 11.5px;
      color: var(--text-3);
    }
  }
}

.ci-status {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 12px;
  font-size: 12.5px;
  color: var(--text-3);

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--text-3);
  }
  &.on {
    color: var(--lime-ink);
    .dot {
      background: var(--lime);
    }
  }
}

.panel-link {
  margin-top: 12px;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 12.5px;
  color: var(--lime-ink);
  cursor: pointer;
  font-family: @font-body;

  &:hover {
    text-decoration: underline;
  }
}


// 设置列表
.settings {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.set-item {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 52px;
  padding: 0 16px;
  border-radius: @r-md;
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: border-color @dur-fast @ease-out, background @dur-fast @ease-out;

  &:not(.static):hover {
    border-color: var(--border-2);
    background: var(--hover);
  }
  &.static {
    cursor: default;
  }
  .si-ico {
    width: 34px;
    height: 34px;
    border-radius: @r-sm;
    background: var(--lime-soft);
    color: var(--lime-ink);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .si-label {
    flex: 1;
    font-size: 14.5px;
    color: var(--text-1);
  }
  .si-arrow {
    color: var(--text-3);
    transform: rotate(-90deg);
  }
  // 行内摘要：不用点进去也知道当前值是多少
  .si-hint {
    font-size: 12px;
    color: var(--text-3);
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 3px 9px;
  }
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 48px;
  border-radius: @r-md;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--red);
  font-family: @font-display;
  font-weight: 600;
  font-size: 14.5px;
  cursor: pointer;
  transition: background @dur-fast @ease-out, border-color @dur-fast @ease-out;

  &:hover {
    background: var(--red-soft);
    border-color: var(--red);
  }
}

// 弹窗
.popup-wrap {
  padding: 24px 20px calc(24px + env(safe-area-inset-bottom));

  .popup-title {
    font-family: @font-display;
    font-size: 17px;
    font-weight: 700;
    margin-bottom: 18px;
    text-align: center;
  }
  .popup-actions {
    margin-top: 18px;
  }
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 0 4px 16px;

  .chip {
    padding: 8px 16px;
    border-radius: 999px;
    background: var(--surface-2);
    color: var(--text-2);
    font-size: 13px;
    border: 1px solid var(--border);
    cursor: pointer;
    transition: all @dur-fast @ease-out;

    &.on {
      background: var(--lime);
      color: var(--on-lime);
      border-color: var(--lime);
      font-weight: 600;
    }
  }
}

.badge-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;

  .badge {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 7px;
    padding: 16px 8px 13px;
    border-radius: @r-md;
    background: var(--lime-soft);
    color: var(--lime-ink);
    font-size: 12.5px;

    .badge-name {
      font-weight: 600;
    }
    .badge-cond {
      font-size: 10.5px;
      line-height: 1.4;
      color: var(--text-3);
      text-align: center;
    }

    .badge-ico {
      width: 44px;
      height: 44px;
      border-radius: @r-md;
      background: var(--lime);
      color: var(--on-lime);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    &.locked {
      background: var(--surface-2);
      color: var(--text-3);
      opacity: 0.7;
      .badge-ico {
        background: var(--surface);
        color: var(--text-3);
        border: 1px solid var(--border);
      }
    }
  }
}

.about-text {
  font-size: 13px;
  line-height: 1.75;
  color: var(--text-2);
  text-align: center;
}

/* ---------------- 大模型配置弹窗 ---------------- */
/* 滚动交给 .van-popup 自身（单一滚动容器），内层不再设 max-height/overflow */
.ai-popup {
  max-height: 82vh;

  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-thumb {
    background: var(--border-2);
    border-radius: 6px;
  }
}

.ai-conf {
  padding: 22px 20px calc(24px + env(safe-area-inset-bottom));

  .popup-title {
    margin-bottom: 8px;
  }
  .ai-conf-tip {
    margin: 0 0 16px;
    font-size: 12px;
    line-height: 1.6;
    color: var(--text-3);

    code {
      font-family: @font-mono;
      font-size: 11.5px;
      padding: 1px 5px;
      border-radius: 4px;
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text-2);
    }
  }
}

.cap-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: @r-md;
  padding: 14px 14px 13px;
  margin-bottom: 12px;

  .cap-head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
  }
  .cap-ico {
    width: 32px;
    height: 32px;
    border-radius: @r-sm;
    background: var(--lime-soft);
    color: var(--lime-ink);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .cap-t {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;

    b {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-1);
      font-family: @font-display;
    }
    span {
      font-size: 11px;
      color: var(--text-3);
    }
  }
}

.field-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  margin: 12px 0 7px;

  .key-hint {
    font-weight: 400;
    font-size: 10.5px;
    font-family: @font-mono;
    color: var(--lime-ink);

    &.dim {
      color: var(--text-3);
    }
  }
}

.prov-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  .prov-chip {
    padding: 7px 13px;
    border-radius: 999px;
    background: var(--surface);
    color: var(--text-2);
    font-size: 12.5px;
    border: 1px solid var(--border);
    cursor: pointer;
    transition: all @dur-fast @ease-out;

    &.on {
      background: var(--lime);
      color: var(--on-lime);
      border-color: var(--lime);
      font-weight: 600;
    }
  }
}

.ai-input {
  width: 100%;
  height: 42px;
  padding: 0 12px;
  border-radius: @r-sm;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-1);
  font-size: 13.5px;
  font-family: @font-mono;
  outline: none;
  box-sizing: border-box;

  &::placeholder {
    color: var(--text-3);
    font-family: @font-body;
  }
  &:focus {
    border-color: var(--lime);
  }
}

.cap-note {
  margin: 10px 0 0;
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-3);
}

/* 免费模型提示 */
.free-note {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}
.ft-badge {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
  color: #0b0d0c;
  background: var(--brand, #c6f24e);
}
</style>
