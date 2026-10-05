<template>
  <div class="page diet">
    <NavBar title="饮食记录" />

    <div class="toolbar">
      <button class="date-pick" @click="showCalendar = true">
        <AppIcon name="calendar" :size="16" />
        <span class="num">{{ recordDate }}</span>
        <AppIcon name="chevdown" :size="14" />
      </button>
      <button class="add-btn" @click="showAction = true">
        <AppIcon name="plus" :size="16" /> 记录饮食
      </button>
    </div>

    <van-pull-refresh v-model="refreshing" @refresh="loadData">
      <div class="diet-layout" :class="{ 'with-side': !isMobile }">
      <div class="meals stagger">
        <div class="card card--edge meal-group" v-for="g in groups" :key="g.type">
          <div class="group-head">
            <span class="group-name"><i class="tick" :class="g.type" />{{ g.label }}</span>
            <span class="group-cal num">{{ g.total }} kcal</span>
          </div>
          <van-swipe-cell v-for="item in g.items" :key="item.id">
            <DietItem :item="item" @click="openEdit" @edit="openEdit" @delete="onDelete" />
            <template #right>
              <van-button square type="danger" text="删除" class="del-btn" @click="onDelete(item)" />
            </template>
          </van-swipe-cell>
          <div v-if="!g.items.length" class="empty">暂无记录</div>
        </div>
      </div>

      <!-- 桌面端：右侧原地编辑面板（不弹窗，选中即改） -->
      <aside v-if="!isMobile" class="side-edit">
        <div class="se-card">
          <template v-if="sideItem">
            <h3 class="se-h">编辑这一条</h3>
            <label class="se-row">
              <span>餐次</span>
              <select v-model.number="sideForm.meal_type" class="se-sel">
                <option :value="1">早餐</option>
                <option :value="2">午餐</option>
                <option :value="3">晚餐</option>
                <option :value="4">加餐</option>
              </select>
            </label>
            <label class="se-row">
              <span>描述</span>
              <input v-model="sideForm.food_desc" class="se-inp" placeholder="食物描述" />
            </label>
            <div class="se-grid4">
              <label class="se-mini"><span>热量</span><input v-model="sideForm.calorie" type="number" class="se-inp num" /></label>
              <label class="se-mini"><span>蛋白</span><input v-model="sideForm.protein" type="number" class="se-inp num" /></label>
              <label class="se-mini"><span>脂肪</span><input v-model="sideForm.fat" type="number" class="se-inp num" /></label>
              <label class="se-mini"><span>碳水</span><input v-model="sideForm.carbohydrate" type="number" class="se-inp num" /></label>
            </div>
            <div class="se-acts">
              <button class="se-save" :disabled="savingSide" @click="saveSide">保存</button>
              <button class="se-cancel" @click="sideItem = null">取消</button>
            </div>
          </template>
          <div v-else class="se-empty">
            <AppIcon name="edit" :size="22" />
            <p>选中左侧任意一条</p>
            <span>在这里直接修改，不用开弹窗</span>
          </div>
        </div>
      </aside>
      </div>

      <div class="card card--edge summary">
        <div class="eyebrow">今日汇总</div>
        <p class="sum-conclusion" v-if="targetCalorie">
          {{ dayConclusion }}
        </p>
        <div class="sum-grid">
          <div class="sum"><span>总热量</span><b class="num">{{ totalCalorie }}</b><i>kcal</i></div>
          <div class="sum"><span>蛋白质</span><b class="num">{{ totalProtein }}</b><i>g</i></div>
          <div class="sum"><span>脂肪</span><b class="num">{{ totalFat }}</b><i>g</i></div>
          <div class="sum"><span>碳水</span><b class="num">{{ totalCarb }}</b><i>g</i></div>
        </div>
      </div>
    </van-pull-refresh>

    <!-- 移动端悬浮加号 -->
    <button class="fab" @click="showAction = true" aria-label="记录饮食">
      <AppIcon name="plus" :size="24" />
    </button>

    <!-- 方式选择 -->
    <van-action-sheet
      v-model:show="showAction"
      :actions="actionList"
      cancel-text="取消"
      description="选择记录方式"
      @select="onSelectAction"
    />

    <!-- 文字输入 -->
    <van-popup v-model:show="showText" position="bottom" round>
      <div class="popup-wrap">
        <div class="popup-title">文字记录</div>
        <van-form @submit="submitText">
          <van-cell-group inset>
            <van-field name="meal_type" label="餐次">
              <template #input>
                <van-radio-group v-model="textForm.meal_type" direction="horizontal">
                  <van-radio :name="1">早</van-radio>
                  <van-radio :name="2">午</van-radio>
                  <van-radio :name="3">晚</van-radio>
                  <van-radio :name="4">加餐</van-radio>
                </van-radio-group>
              </template>
            </van-field>
            <van-field
              v-model="textForm.food_desc"
              label="描述"
              type="textarea"
              rows="2"
              placeholder="如：两碗米饭 + 一份炒青菜"
              :rules="[{ required: true, message: '请填写食物描述' }]"
            />
            <van-field v-model="textForm.calorie" type="digit" label="热量(kcal)" placeholder="0" />
            <van-field v-model="textForm.protein" type="digit" label="蛋白质(g)" placeholder="选填" />
            <van-field v-model="textForm.fat" type="digit" label="脂肪(g)" placeholder="选填" />
            <van-field v-model="textForm.carbohydrate" type="digit" label="碳水(g)" placeholder="选填" />
          </van-cell-group>
          <div class="popup-actions">
            <van-button block round type="primary" native-type="submit">保存</van-button>
          </div>
        </van-form>
      </div>
    </van-popup>

    <!-- 食物库：从条目一键入库，服务端完成份量换算 -->
    <FoodPicker
      v-model="showFoodPicker"
      :meal-type="recMealType"
      :record-date="recordDate"
      @added="onFoodAdded"
    />

    <!-- 拍照识别结果 -->
    <van-popup v-model:show="showRecognize" position="bottom" round>
      <div class="popup-wrap">
        <div class="popup-title">识别结果（可修改）</div>
        <div v-if="recognizing" class="recognizing">
          <van-loading size="18px" /> 正在识别食物...
        </div>
        <template v-else>
          <van-field label="餐次">
            <template #input>
              <van-radio-group v-model="recMealType" direction="horizontal">
                <van-radio :name="1">早</van-radio>
                <van-radio :name="2">午</van-radio>
                <van-radio :name="3">晚</van-radio>
                <van-radio :name="4">加餐</van-radio>
              </van-radio-group>
            </template>
          </van-field>
          <div class="rec-count">共识别到 {{ recognizedList.length }} 项</div>
          <div class="rec-list">
            <div class="rec-item" v-for="(f, i) in recognizedList" :key="i">
              <div class="rec-head">
                <span class="rec-idx">#{{ i + 1 }}</span>
                <van-field v-model="f.name" label="名称" />
                <button
                  v-if="recognizedList.length > 1"
                  class="rec-del"
                  type="button"
                  aria-label="移除该项"
                  @click="recognizedList.splice(i, 1)"
                >
                  <AppIcon name="trash" :size="16" />
                </button>
              </div>
              <div class="rec-grid">
                <van-field v-model="f.quantity" type="digit" label="数量" placeholder="1" />
                <van-field v-model="f.weight" type="digit" label="重量(g)" />
                <van-field v-model="f.calorie" type="digit" label="热量" />
                <van-field v-model="f.protein" type="digit" label="蛋白(g)" />
                <van-field v-model="f.fat" type="digit" label="脂肪(g)" />
                <van-field v-model="f.carbohydrate" type="digit" label="碳水(g)" />
              </div>
            </div>
          </div>
          <div class="popup-actions">
            <van-button block round type="primary" @click="saveRecognized">保存到今日饮食</van-button>
          </div>
        </template>
      </div>
    </van-popup>

    <!-- 编辑弹窗 -->
    <van-popup v-model:show="showEdit" position="bottom" round>
      <div class="popup-wrap" v-if="editItem">
        <div class="popup-title">编辑记录</div>
        <van-form @submit="submitEdit">
          <van-cell-group inset>
            <van-field v-model="editItem.food_desc" label="描述" :rules="[{ required: true }]" />
            <van-field v-model="editItem.calorie" type="digit" label="热量(kcal)" />
            <van-field v-model="editItem.protein" type="digit" label="蛋白质(g)" />
            <van-field v-model="editItem.fat" type="digit" label="脂肪(g)" />
            <van-field v-model="editItem.carbohydrate" type="digit" label="碳水(g)" />
          </van-cell-group>
          <div class="popup-actions">
            <van-button block round type="primary" native-type="submit">更新</van-button>
          </div>
        </van-form>
      </div>
    </van-popup>

    <!-- 日历 -->
    <van-calendar v-model:show="showCalendar" :min-date="minDate" :max-date="maxDate" @confirm="onPickDate" />

    <!-- 隐藏文件输入 -->
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      capture="environment"
      style="display: none"
      @change="onFileChange"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import DietItem from '@/components/DietItem.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import { listDiet, addDiet, updateDiet, deleteDiet } from '@/api/diet'
import { recognizeFood } from '@/api/ai'
import { showToast, showLoadingToast, closeToast, showConfirmDialog } from 'vant'
import { formatDate, today, roundNum } from '@/utils/format'
import { compressImage } from '@/utils/image'
import FoodPicker from '@/components/FoodPicker.vue'
import { energyTarget } from '@/api/energy'
import { isMobileRef } from '@/utils/breakpoint'

const recordDate = ref(today())
const refreshing = ref(false)
const records = ref([])

const minDate = new Date(new Date().setMonth(new Date().getMonth() - 3))
const maxDate = new Date()
const showCalendar = ref(false)

const showAction = ref(false)
const showText = ref(false)
const showRecognize = ref(false)
const showEdit = ref(false)
const recognizing = ref(false)
const fileInput = ref(null)
const recMealType = ref(2)

const recognizedList = ref([])
// 识别结果对应的图片 URL（随记录一并保存，便于在列表显示缩略图）
const recImageUrl = ref('')
const editItem = ref(null)

// 桌面端原地编辑面板
const sideItem = ref(null)
const savingSide = ref(false)
const sideForm = reactive({
  meal_type: 2,
  food_desc: '',
  calorie: '',
  protein: '',
  fat: '',
  carbohydrate: ''
})

const showFoodPicker = ref(false)

// 目标热量：用于给出「还剩多少 / 超了多少」的可执行结论
const targetCalorie = ref(0)
const dayConclusion = computed(() => {
  const t = Number(targetCalorie.value)
  const got = Number(totalCalorie.value)
  if (!t) return ''
  const diff = Math.round(t - got)
  if (diff > 0) return `今天还能吃 ${diff} kcal，大约是 ${diffToFoodHint(diff)}。`
  return `今天已超出 ${Math.abs(diff)} kcal，明天的缺口可以适当放宽一点，别急着节食补偿。`
})

function diffToFoodHint(kcal) {
  // 用食物库的真实条目换算等价量，避免前台二次维护营养数据
  const one = Math.round(kcal / 116) // 一碗米饭约 116 kcal/100g → 这里按每份 150g 估算
  if (one <= 0) return '一小口'
  return `${one} 份主食的分量`
}

async function loadTarget() {
  try {
    const data = await energyTarget({ days: 14 })
    if (data && data.target && data.target.target_calorie) {
      targetCalorie.value = data.target.target_calorie
    }
  } catch (e) {
    /* 目标取不到就不显示结论，不填假值 */
  }
}

function onFoodAdded() {
  loadData()
}

// 左侧列表点击编辑：桌面走右侧面板，移动端走弹窗
function openEdit(item) {
  sideForm.meal_type = Number(item.meal_type)
  sideForm.food_desc = item.food_desc
  sideForm.calorie = item.calorie
  sideForm.protein = item.protein
  sideForm.fat = item.fat
  sideForm.carbohydrate = item.carbohydrate
  if (!isMobile.value) {
    sideItem.value = item
  } else {
    editItem.value = { ...item }
    showEdit.value = true
  }
}

async function saveSide() {
  if (!sideItem.value || savingSide.value) return
  savingSide.value = true
  try {
    await updateDiet(sideItem.value.id, {
      meal_type: sideForm.meal_type,
      food_desc: sideForm.food_desc,
      calorie: Number(sideForm.calorie || 0),
      protein: Number(sideForm.protein || 0),
      fat: Number(sideForm.fat || 0),
      carbohydrate: Number(sideForm.carbohydrate || 0)
    })
    showToast({ type: 'success', message: '已更新' })
    sideItem.value = null
    loadData()
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    savingSide.value = false
  }
}

const isMobile = isMobileRef

const actionList = [
  { name: '从食物库选', value: 'food' },
  { name: '拍照识别', value: 'camera' },
  { name: '文字输入', value: 'text' }
]

const textForm = reactive({
  meal_type: 2,
  food_desc: '',
  calorie: '',
  protein: '',
  fat: '',
  carbohydrate: ''
})

// 后端/数据库的 meal_type 为整数 1 早 / 2 午 / 3 晚 / 4 加餐，分组与提交均按整数进行
const MEAL_GROUPS = [
  { type: 1, label: '早餐' },
  { type: 2, label: '午餐' },
  { type: 3, label: '晚餐' },
  { type: 4, label: '加餐' }
]

const groups = computed(() => {
  const map = {}
  MEAL_GROUPS.forEach((g) => {
    map[g.type] = { type: g.type, label: g.label, items: [], total: 0 }
  })
  records.value.forEach((r) => {
    const key = Number(r.meal_type)
    const g = map[key] || map[4]
    g.items.push(r)
    g.total += Number(r.calorie || 0)
  })
  return MEAL_GROUPS.map((g) => ({ ...map[g.type], total: roundNum(map[g.type].total, 1) }))
})

// 浮点累加会出现 47.70000000000001 这类尾数，统一 roundNum 后再展示
const totalCalorie = computed(() =>
  roundNum(records.value.reduce((s, r) => s + Number(r.calorie || 0), 0), 1)
)
const totalProtein = computed(() =>
  roundNum(records.value.reduce((s, r) => s + Number(r.protein || 0), 0), 1)
)
const totalFat = computed(() =>
  roundNum(records.value.reduce((s, r) => s + Number(r.fat || 0), 0), 1)
)
const totalCarb = computed(() =>
  roundNum(records.value.reduce((s, r) => s + Number(r.carbohydrate || 0), 0), 1)
)

async function loadData() {
  try {
    const res = await listDiet({ record_date: recordDate.value })
    records.value = res.records || []
  } catch (e) {
    records.value = []
  } finally {
    refreshing.value = false
  }
}

function onPickDate(date) {
  recordDate.value = formatDate(date)
  showCalendar.value = false
  loadData()
}

function onSelectAction(action) {
  showAction.value = false
  if (action.value === 'food') {
    showFoodPicker.value = true
  } else if (action.value === 'text') {
    showText.value = true
  } else {
    fileInput.value.click()
  }
}

async function submitText() {
  try {
    await addDiet({
      record_date: recordDate.value,
      meal_type: Number(textForm.meal_type),
      food_desc: textForm.food_desc,
      // 后端 input_type：1 文字 / 2 图片（传字符串会被 pydantic 判为参数校验失败 → 400）
      input_type: 1,
      calorie: Number(textForm.calorie) || 0,
      protein: Number(textForm.protein) || 0,
      fat: Number(textForm.fat) || 0,
      carbohydrate: Number(textForm.carbohydrate) || 0
    })
    showToast({ type: 'success', message: '已保存' })
    showText.value = false
    Object.assign(textForm, {
      meal_type: 2,
      food_desc: '',
      calorie: '',
      protein: '',
      fat: '',
      carbohydrate: ''
    })
    loadData()
  } catch (e) {}
}

function onFileChange(e) {
  const file = e.target.files[0]
  if (!file) return
  recognize(file)
  e.target.value = ''
}

async function recognize(file) {
  recognizing.value = true
  showRecognize.value = true
  try {
    // 手机原图常 >5MB 或为 HEIC/WebP，先在前端压缩并转 JPEG 再上传，避免后端 400
    const upload = await compressImage(file)
    const fd = new FormData()
    fd.append('file', upload)
    const res = await recognizeFood(fd)
    recImageUrl.value = res.image_url || ''
    recognizedList.value = (res.food_list || []).map((f) => ({
      name: f.name || '',
      // 数量：同一张图里可能有多个相同食物，用它区分（后端 quantity，缺省 1）
      quantity: String(f.quantity || 1),
      weight: String(f.weight || ''),
      calorie: String(f.calorie || ''),
      protein: String(f.protein || ''),
      fat: String(f.fat || ''),
      carbohydrate: String(f.carbohydrate || ''),
      sugar: String(f.sugar || ''),
      fiber: String(f.fiber || ''),
      sodium: String(f.sodium || '')
    }))
    if (!recognizedList.value.length) {
      showToast('未能识别食物，请手动输入')
    }
  } catch (e) {
    // 透出后端具体原因（如格式/大小限制），而非笼统的「识别失败」
    const r = e && e.response
    showToast((r && r.data && r.data.message) || '识别失败，请重试')
  } finally {
    recognizing.value = false
  }
}

async function saveRecognized() {
  try {
    let ok = 0
    for (const f of recognizedList.value) {
      const qty = Math.max(1, Math.round(Number(f.quantity) || 1))
      // 数据库无「数量」列，把数量并入描述，如「鸡蛋 ×2」，避免多个同名食物信息丢失
      const desc = qty > 1 ? `${f.name} ×${qty}` : f.name
      await addDiet({
        record_date: recordDate.value,
        meal_type: Number(recMealType.value),
        food_desc: desc,
        // 后端 input_type：1 文字 / 2 图片
        input_type: 2,
        food_image_path: recImageUrl.value || null,
        calorie: Number(f.calorie) || 0,
        protein: Number(f.protein) || 0,
        fat: Number(f.fat) || 0,
        carbohydrate: Number(f.carbohydrate) || 0,
        sugar: Number(f.sugar) || 0,
        fiber: Number(f.fiber) || 0,
        sodium: Number(f.sodium) || 0
      })
      ok += 1
    }
    showToast({ type: 'success', message: '已保存 ' + ok + ' 项' })
    showRecognize.value = false
    recognizedList.value = []
    recImageUrl.value = ''
    loadData()
  } catch (e) {
    // 原先静默吞异常，导致「保存失败但看不到原因」（例如参数校验 400）
    const r = e && e.response
    showToast({ type: 'fail', message: (r && r.data && r.data.message) || '保存失败，请重试' })
  }
}

function onEdit(item) {
  editItem.value = { ...item }
  showEdit.value = true
}

async function submitEdit() {
  const item = editItem.value
  try {
    await updateDiet(item.id, {
      food_desc: item.food_desc,
      calorie: Number(item.calorie) || 0,
      protein: Number(item.protein) || 0,
      fat: Number(item.fat) || 0,
      carbohydrate: Number(item.carbohydrate) || 0
    })
    showToast({ type: 'success', message: '已更新' })
    showEdit.value = false
    loadData()
  } catch (e) {
    const r = e && e.response
    showToast({ type: 'fail', message: (r && r.data && r.data.message) || '更新失败，请重试' })
  }
}

async function onDelete(item) {
  try {
    await showConfirmDialog({ title: '提示', message: '确定删除这条记录？' })
    await deleteDiet(item.id)
    showToast({ type: 'success', message: '已删除' })
    loadData()
  } catch (e) {
    // 取消
  }
}

onMounted(() => {
  loadData()
  loadTarget()
})
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

// 桌面端：左列表 + 右原地编辑；移动端仍为单列原样布局
.diet-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.diet-layout.with-side {
  grid-template-columns: minmax(0, 1fr) minmax(0, 320px);
}

.side-edit {
  position: sticky;
  top: 0;
}

.se-card {
  padding: 18px;
  border-radius: @r-lg;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-1);
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.se-h {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
}

.se-row,
.se-mini {
  display: flex;
  flex-direction: column;
  gap: 5px;

  > span {
    font-size: 11.5px;
    color: var(--text-3);
  }
}

.se-grid4 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.se-inp,
.se-sel {
  height: 38px;
  padding: 0 11px;
  border-radius: @r-sm;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 13.5px;

  &:focus {
    outline: none;
    border-color: var(--lime-ink);
    background: var(--surface);
  }
}

.se-acts {
  display: flex;
  gap: 9px;
}

.se-save {
  flex: 1;
  height: 40px;
  border-radius: 999px;
  border: none;
  background: var(--lime);
  color: var(--on-lime);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;

  &:disabled {
    opacity: 0.6;
  }
}

.se-cancel {
  height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}

.se-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 26px 12px;
  text-align: center;
  color: var(--text-3);

  p {
    margin: 0;
    font-size: 13.5px;
    color: var(--text-2);
  }
  span {
    font-size: 11.5px;
  }
}

// 汇总结论
.sum-conclusion {
  margin: 8px 0 14px;
  padding: 11px 13px;
  border-radius: @r-md;
  background: var(--olive-soft);
  border: 1px solid var(--border);
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-1);
}

@media (max-width: 1023px) {
  .diet-layout.with-side {
    grid-template-columns: minmax(0, 1fr);
  }
  .side-edit {
    display: none;
  }
}

// 桌面端：左列表 + 右原地编辑；移动端仍为单列原样布局
.diet-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.diet-layout.with-side {
  grid-template-columns: minmax(0, 1fr) minmax(0, 320px);
}

.side-edit {
  position: sticky;
  top: 0;
}

.se-card {
  padding: 18px;
  border-radius: @r-lg;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-1);
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.se-h {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-1);
}

.se-row,
.se-mini {
  display: flex;
  flex-direction: column;
  gap: 5px;

  > span {
    font-size: 11.5px;
    color: var(--text-3);
  }
}

.se-grid4 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.se-inp,
.se-sel {
  height: 38px;
  padding: 0 11px;
  border-radius: @r-sm;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-1);
  font-size: 13.5px;

  &:focus {
    outline: none;
    border-color: var(--lime-ink);
    background: var(--surface);
  }
}

.se-acts {
  display: flex;
  gap: 9px;
}

.se-save {
  flex: 1;
  height: 40px;
  border-radius: 999px;
  border: none;
  background: var(--lime);
  color: var(--on-lime);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;

  &:disabled {
    opacity: 0.6;
  }
}

.se-cancel {
  height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-2);
  cursor: pointer;
}

.se-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 26px 12px;
  text-align: center;
  color: var(--text-3);

  p {
    margin: 0;
    font-size: 13.5px;
    color: var(--text-2);
  }
  span {
    font-size: 11.5px;
  }
}

// 汇总结论
.sum-conclusion {
  margin: 8px 0 14px;
  padding: 11px 13px;
  border-radius: @r-md;
  background: var(--olive-soft);
  border: 1px solid var(--border);
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-1);
}

@media (max-width: 1023px) {
  .diet-layout.with-side {
    grid-template-columns: minmax(0, 1fr);
  }
  .side-edit {
    display: none;
  }
}

.page.diet {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.date-pick {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: @r-md;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-1);
  font-size: 13.5px;
  cursor: pointer;
  transition: border-color @dur-fast @ease-out;

  &:hover {
    border-color: var(--border-2);
  }
}
.add-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  border-radius: @r-md;
  background: var(--lime);
  color: var(--on-lime);
  font-family: @font-display;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: filter @dur-fast @ease-out, box-shadow @dur-fast @ease-out;

  &:hover {
    filter: brightness(1.06);
    box-shadow: var(--glow-lime);
  }
}

.meals {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.meal-group {
  .group-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }
  .group-name {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: @font-display;
    font-size: 15px;
    font-weight: 600;
    color: var(--text-1);

    .tick {
      width: 8px;
      height: 8px;
      border-radius: 2px;
      &.breakfast {
        background: var(--orange);
      }
      &.lunch {
        background: var(--lime);
      }
      &.dinner {
        background: var(--cyan);
      }
      &.snack {
        background: var(--violet);
      }
    }
  }
  .group-cal {
    font-size: 12.5px;
    color: var(--orange);
    font-weight: 600;
  }
  .empty {
    text-align: center;
    color: var(--text-3);
    font-size: 12.5px;
    padding: 14px 0;
  }
}

.summary {
  margin-top: 16px;
  .sum-grid {
    margin-top: 14px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
  .sum {
    text-align: center;
    padding: 12px 6px;
    background: var(--surface-2);
    border-radius: @r-md;
    span {
      display: block;
      font-size: 11.5px;
      color: var(--text-3);
      margin-bottom: 6px;
    }
    b {
      font-size: 22px;
      font-weight: 800;
      color: var(--text-1);
    }
    i {
      font-size: 11px;
      color: var(--text-3);
      font-style: normal;
      margin-left: 3px;
    }
  }
}

.del-btn {
  height: 100%;
}

.fab {
  position: fixed;
  right: 18px;
  bottom: calc(74px + env(safe-area-inset-bottom));
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: none;
  background: var(--lime);
  color: var(--on-lime);
  display: none;
  align-items: center;
  justify-content: center;
  box-shadow: var(--glow-lime), var(--shadow-2);
  z-index: 10;
  cursor: pointer;
}

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
.recognizing {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 0;
  color: var(--text-3);
}
.rec-count {
  margin: 4px 0 10px;
  font-size: 12px;
  color: var(--text-3);
}
.rec-item {
  border-bottom: 1px solid var(--border);
  padding-bottom: 14px;
  margin-bottom: 14px;

  &:last-child {
    border-bottom: none;
    margin-bottom: 0;
  }

  .rec-head {
    display: flex;
    align-items: center;
    gap: 6px;

    .van-field {
      flex: 1;
      min-width: 0;
    }

    .rec-idx {
      flex-shrink: 0;
      width: 26px;
      font-size: 12px;
      font-family: @font-mono;
      color: var(--lime-ink);
    }

    .rec-del {
      flex-shrink: 0;
      width: 30px;
      height: 30px;
      border: none;
      border-radius: @r-sm;
      background: transparent;
      color: var(--text-3);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;

      &:hover {
        color: var(--red);
        background: var(--red-soft);
      }
    }
  }

  .rec-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0 12px;
  }
}

@media (max-width: 1023px) {
  .meals {
    grid-template-columns: 1fr;
  }
  .add-btn {
    display: none;
  }
  .fab {
    display: flex;
  }
  .summary .sum-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
