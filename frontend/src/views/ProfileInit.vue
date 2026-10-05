<template>
  <div class="page profile-page">
    <NavBar title="完善资料" :show-back="false" />

    <div class="steps">
      <div class="step" :class="{ active: step === 1, done: step > 1 }">
        <span class="num num-font">1</span>身体数据
      </div>
      <div class="line" />
      <div class="step" :class="{ active: step === 2 }">
        <span class="num num-font">2</span>习惯偏好
      </div>
    </div>

    <!-- 步骤一 -->
    <div v-show="step === 1" class="card card--edge form-card">
      <div class="eyebrow">基础身体数据</div>
      <van-form class="mt">
        <van-cell-group inset>
          <van-field label="性别" :border="false">
            <template #input>
              <van-radio-group v-model="form.gender" direction="horizontal">
                <van-radio name="male">男</van-radio>
                <van-radio name="female">女</van-radio>
              </van-radio-group>
            </template>
          </van-field>
          <van-field v-model="form.age" type="digit" label="年龄" placeholder="岁">
            <template #right-icon>岁</template>
          </van-field>
          <van-field v-model="form.height" type="digit" label="身高" placeholder="cm">
            <template #right-icon>cm</template>
          </van-field>
          <van-field v-model="form.current_weight" type="digit" label="当前体重" placeholder="kg">
            <template #right-icon>kg</template>
          </van-field>
          <van-field v-model="form.target_weight" type="digit" label="目标体重" placeholder="kg">
            <template #right-icon>kg</template>
          </van-field>
        </van-cell-group>
      </van-form>
    </div>

    <!-- 步骤二 -->
    <div v-show="step === 2" class="card card--edge form-card">
      <div class="eyebrow">活动水平</div>
      <van-radio-group v-model="form.activity_level" class="mt">
        <van-cell
          v-for="opt in activityOptions"
          :key="opt.value"
          :title="opt.label"
          :label="opt.desc"
          clickable
          @click="form.activity_level = opt.value"
        >
          <template #right-icon>
            <van-radio :name="opt.value" />
          </template>
        </van-cell>
      </van-radio-group>

      <div class="eyebrow mt-lg">饮食偏好（可多选）</div>
      <div class="chips">
        <span
          v-for="p in dietOptions"
          :key="p"
          class="chip"
          :class="{ on: form.diet_preference.includes(p) }"
          @click="toggleDiet(p)"
        >
          {{ p }}
        </span>
      </div>

      <van-field
        v-model="form.diet_avoid"
        type="textarea"
        label="忌口/过敏"
        placeholder="如：不吃香菜、海鲜过敏（选填）"
        autosize
        rows="1"
      />
    </div>

    <!-- 实时预览 -->
    <div class="card card--edge preview">
      <div class="eyebrow">实时评估</div>
      <div class="preview-row">
        <span>BMI</span>
        <b class="num" :class="bmiClass">{{ bmi }} {{ bmiLevelText }}</b>
      </div>
      <div class="preview-row">
        <span>推荐热量</span>
        <b class="num">{{ recommend }} kcal/天</b>
      </div>
      <div class="preview-row">
        <span>预计达成</span>
        <b class="num">约 {{ weeks }} 周</b>
      </div>
    </div>

    <div class="footer-actions">
      <van-button v-if="step === 2" plain type="primary" block round @click="step = 1">上一步</van-button>
      <van-button v-if="step === 1" type="primary" block round @click="nextStep">下一步</van-button>
      <van-button v-else type="primary" block round :loading="loading" loading-text="保存中..." @click="onSubmit">
        完成
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import { useUserStore } from '@/store/modules/user'
import { updateProfile, updatePreference } from '@/api/auth'
import { showToast, showLoadingToast, closeToast } from 'vant'
import {
  calcBMI,
  bmiLevel,
  calcBMR,
  calcTDEE,
  calcRecommendCalorie,
  estimateWeeks,
  GENDER_TO_INT,
  activityToInt
} from '@/utils/common'

const router = useRouter()
const userStore = useUserStore()
const step = ref(1)
const loading = ref(false)

const form = reactive({
  gender: 'female',
  age: '',
  height: '',
  current_weight: '',
  target_weight: '',
  activity_level: 'light',
  diet_preference: [],
  diet_avoid: ''
})

const activityOptions = [
  { value: 'sedentary', label: '久坐少动', desc: '几乎不运动 / 办公室为主' },
  { value: 'light', label: '轻度活动', desc: '每周运动 1-3 次' },
  { value: 'moderate', label: '中度活动', desc: '每周运动 3-5 次' },
  { value: 'active', label: '高强度活动', desc: '每周运动 6 次以上 / 体力劳动' }
]

const dietOptions = ['高蛋白', '低脂肪', '低碳水', '素食', '少油少盐', '清淡', '均衡']

function toggleDiet(p) {
  const i = form.diet_preference.indexOf(p)
  if (i >= 0) form.diet_preference.splice(i, 1)
  else form.diet_preference.push(p)
}

const bmi = computed(() => {
  if (!form.current_weight || !form.height) return '—'
  return calcBMI(Number(form.current_weight), Number(form.height))
})
const bmiLevelText = computed(() => (bmi.value === '—' ? '' : bmiLevel(Number(bmi.value))))
const bmiClass = computed(() => {
  if (bmi.value === '—') return ''
  const v = Number(bmi.value)
  if (v < 18.5 || v >= 28) return 'warn'
  return 'good'
})

const bmr = computed(() =>
  calcBMR({
    gender: form.gender,
    weight: Number(form.current_weight),
    height: Number(form.height),
    age: Number(form.age)
  })
)
const tdee = computed(() => calcTDEE(bmr.value, form.activity_level))
const recommend = computed(() =>
  bmr.value ? calcRecommendCalorie(tdee.value, bmr.value) : '—'
)
const weeks = computed(() => {
  if (!form.current_weight || !form.target_weight) return '—'
  return estimateWeeks(
    Number(form.current_weight),
    Number(form.target_weight),
    Number(recommend.value),
    tdee.value
  )
})

function nextStep() {
  if (!form.age || !form.height || !form.current_weight || !form.target_weight) {
    showToast('请先填写完整的身体数据')
    return
  }
  step.value = 2
}

async function onSubmit() {
  loading.value = true
  showLoadingToast({ message: '保存中...', forbidClick: true })
  try {
    const profilePayload = {
      // 后端 ProfileUpdate 要求 int：gender 0 女 / 1 男，activity_level 1~4
      gender: GENDER_TO_INT[form.gender] ?? 0,
      age: Number(form.age),
      height: Number(form.height),
      current_weight: Number(form.current_weight),
      target_weight: Number(form.target_weight),
      activity_level: activityToInt(form.activity_level)
    }
    await updateProfile(profilePayload)
    if (form.diet_preference.length) {
      await updatePreference({ diet_preference: form.diet_preference.join(',') })
    }
    userStore.updateUserInfo({
      ...profilePayload,
      diet_preference: form.diet_preference.join(',')
    })
    userStore.setProfileCompleteFlag(true)
    showToast({ type: 'success', message: '资料已保存' })
    router.replace('/home')
  } catch (e) {
    // 拦截器已提示
  } finally {
    closeToast()
    loading.value = false
  }
}
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.profile-page {
  max-width: 640px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mt {
  margin-top: 14px;
}
.mt-lg {
  margin-top: 22px;
}

.eyebrow {
  margin-bottom: 2px;
}

.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 0 2px;

  .step {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-3);
    font-size: 13px;

    .num {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--surface-2);
      border: 1px solid var(--border);
      color: var(--text-3);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
    }
    &.active {
      color: var(--text-1);
      font-weight: 600;
      .num {
        background: var(--lime);
        border-color: var(--lime);
        color: var(--on-lime);
      }
    }
    &.done .num {
      background: var(--lime);
      border-color: var(--lime);
      color: var(--on-lime);
    }
  }
  .line {
    width: 46px;
    height: 1px;
    background: var(--border-2);
  }
}

.form-card {
  :deep(.van-field) {
    padding: 12px 0;
  }
}
.num-font {
  font-family: @font-mono;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 12px 0 16px;

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

.preview {
  .preview-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 13px 0;
    border-bottom: 1px solid var(--border);
    font-size: 14px;

    &:last-child {
      border-bottom: none;
    }
    span {
      color: var(--text-3);
    }
    b {
      color: var(--text-1);

      &.good {
        color: var(--lime-ink);
      }
      &.warn {
        color: var(--orange);
      }
    }
  }
}

.footer-actions {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}
</style>
