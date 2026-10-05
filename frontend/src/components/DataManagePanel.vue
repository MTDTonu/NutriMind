<template>
  <div class="dm">
    <!-- 导出 -->
    <section class="dm-sec">
      <h4 class="dm-h">导出我的数据</h4>
      <p class="dm-tip">
        导出的是原始记录本身，数字与界面显示完全一致，不做任何二次加工。
        CSV 带 UTF-8 表头，可直接用 Excel 打开。
      </p>

      <div class="dm-row">
        <span class="dm-label">时间范围</span>
        <div class="chips">
          <button
            v-for="r in ranges"
            :key="r.days"
            class="chip"
            :class="{ on: days === r.days }"
            @click="days = r.days"
          >
            {{ r.label }}
          </button>
        </div>
      </div>

      <div class="dm-row">
        <span class="dm-label">文件格式</span>
        <div class="chips">
          <button
            v-for="f in formats"
            :key="f.value"
            class="chip"
            :class="{ on: format === f.value }"
            @click="format = f.value"
          >
            {{ f.label }}
          </button>
        </div>
      </div>

      <button class="dm-btn" :disabled="exporting" @click="doExport">
        <AppIcon name="display" :size="16" />
        {{ exporting ? '正在生成…' : `导出 ${format.toUpperCase()} 文件` }}
      </button>
    </section>

    <!-- 导入 -->
    <section class="dm-sec">
      <h4 class="dm-h">导入历史数据</h4>
      <p class="dm-tip">
        CSV 首行必须是表头。同一天重复导入不会生成重复记录（已有记录会被更新）。
      </p>

      <div class="dm-row">
        <span class="dm-label">数据类型</span>
        <div class="chips">
          <button
            v-for="k in kinds"
            :key="k.value"
            class="chip"
            :class="{ on: kind === k.value }"
            @click="kind = k.value"
          >
            {{ k.label }}
          </button>
        </div>
      </div>

      <!-- 模板：直接把要求摊开，别让用户猜 -->
      <div class="dm-tpl">
        <span class="tpl-k">表头示例</span>
        <code>{{ kind === 'weight' ? '日期,体重,体脂率,腰围' : '日期,餐次,食物,热量,蛋白质,脂肪,碳水' }}</code>
      </div>
      <p class="dm-tip small">
        餐次支持：早餐 / 午餐 / 晚餐 / 加餐（或 1–4）；日期支持 YYYY-MM-DD、YYYY/MM/DD 等常见写法。
      </p>

      <label class="dm-file">
        <input
          ref="fileRef"
          type="file"
          accept=".csv,text/csv"
          @change="onPick"
          hidden
        />
        <AppIcon name="plus" :size="16" />
        {{ file ? file.name : '选择 CSV 文件（≤ 2MB）' }}
      </label>

      <button class="dm-btn" :disabled="!file || importing" @click="doImport">
        <AppIcon name="refresh" :size="16" />
        {{ importing ? '正在导入…' : '开始导入' }}
      </button>

      <!-- 结果：一行都不静默丢弃 -->
      <div v-if="result" class="dm-result">
        <div class="dmr-line">
          <span>新增</span><b class="num">{{ result.inserted }}</b>
          <span>更新</span><b class="num">{{ result.updated }}</b>
          <span>重复跳过</span><b class="num">{{ result.skipped }}</b>
        </div>
        <div v-if="result.errors && result.errors.length" class="dmr-err">
          <p v-for="e in result.errors.slice(0, 5)" :key="e.row">
            第 {{ e.row }} 行：{{ e.reason }}
          </p>
          <p v-if="result.errors.length > 5" class="more">
            其余 {{ result.errors.length - 5 }} 行同样失败，请按提示修正表头后重试。
          </p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { showToast } from 'vant'
import AppIcon from '@/components/icons/AppIcon.vue'
import { exportData, importData } from '@/api/data'

const RANGES = [
  { days: 7, label: '近 7 天' },
  { days: 30, label: '近 30 天' },
  { days: 0, label: '全部' }
]
const FORMATS = [
  { value: 'csv', label: 'CSV（Excel）' },
  { value: 'json', label: 'JSON（全量包）' }
]
const KINDS = [
  { value: 'weight', label: '体重记录' },
  { value: 'diet', label: '饮食记录' }
]

const ranges = RANGES
const formats = FORMATS
const kinds = KINDS

const days = ref(30)
const format = ref('csv')
const kind = ref('weight')

const file = ref(null)
const fileRef = ref(null)
const exporting = ref(false)
const importing = ref(false)
const result = ref(null)

function onPick(e) {
  const f = e.target.files && e.target.files[0]
  if (!f) return
  if (f.size > 2 * 1024 * 1024) {
    showToast({ type: 'fail', message: '文件超过 2MB，请拆分后再导入' })
    return
  }
  file.value = f
  result.value = null
}

async function doExport() {
  exporting.value = true
  try {
    // responseType=blob：拿到二进制后再用 ObjectURL 触发下载，避免暴露 Token 在 URL 上
    const blob = await exportData({ days: days.value, format: format.value })
    const url = window.URL.createObjectURL(new Blob([blob]))
    const a = document.createElement('a')
    const today = new Date().toISOString().slice(0, 10)
    a.href = url
    a.download = `nutrimind-export-${today}.${format.value}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    showToast({ type: 'success', message: '已导出' })
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    exporting.value = false
  }
}

async function doImport() {
  if (!file.value) return
  importing.value = true
  try {
    result.value = await importData(kind.value, file.value)
    showToast({ type: 'success', message: '导入完成' })
  } catch (e) {
    /* 拦截器已提示 */
  } finally {
    importing.value = false
  }
}
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.dm {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.dm-sec {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dm-h {
  margin: 0;
  font-size: 14.5px;
  font-weight: 700;
  color: var(--text-1);
}

.dm-tip {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-2);

  &.small {
    font-size: 11.5px;
    color: var(--text-3);
    margin-top: -4px;
  }
}

.dm-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;

  .dm-label {
    width: 56px;
    flex-shrink: 0;
    font-size: 12.5px;
    color: var(--text-3);
  }
}

.chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chip {
  padding: 7px 13px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  font-size: 12.5px;
  color: var(--text-2);
  cursor: pointer;
  transition: all @dur-fast @ease-out;

  &:hover {
    background: var(--hover);
  }
  &.on {
    border-color: var(--lime-ink);
    background: var(--olive-soft);
    color: var(--text-1);
    font-weight: 600;
  }
}

.dm-tpl {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 12px;
  border-radius: @r-sm;
  background: var(--surface-2);
  border: 1px dashed var(--border-2);

  .tpl-k {
    font-size: 11.5px;
    color: var(--text-3);
    flex-shrink: 0;
  }
  code {
    font-size: 11.5px;
    color: var(--text-1);
    word-break: break-all;
  }
}

.dm-file {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 52px;
  border-radius: @r-md;
  border: 1.5px dashed var(--border-2);
  background: var(--surface-2);
  color: var(--text-2);
  font-size: 13px;
  cursor: pointer;
  padding: 0 12px;
  text-align: center;
  transition: border-color @dur-fast @ease-out, color @dur-fast @ease-out;

  &:hover {
    border-color: var(--lime-ink);
    color: var(--text-1);
  }
}

.dm-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 44px;
  border-radius: 999px;
  border: none;
  background: var(--lime);
  color: var(--on-lime);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--glow-lime);

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
    box-shadow: none;
  }
}

.dm-result {
  padding: 12px 13px;
  border-radius: @r-md;
  background: var(--olive-soft);
  border: 1px solid var(--border);

  .dmr-line {
    display: flex;
    align-items: baseline;
    gap: 6px;
    font-size: 12.5px;
    color: var(--text-2);
    flex-wrap: wrap;

    b {
      font-size: 15px;
      font-weight: 700;
      color: var(--text-1);
      margin-right: 10px;
    }
  }
  .dmr-err {
    margin-top: 9px;
    padding-top: 9px;
    border-top: 1px solid var(--border);

    p {
      margin: 0 0 4px;
      font-size: 11.5px;
      line-height: 1.6;
      color: var(--clay);
    }
    .more {
      color: var(--text-3);
    }
  }
}
</style>
