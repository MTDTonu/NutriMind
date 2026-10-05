<template>
  <div class="diet-item">
    <div class="food-thumb" v-if="item.food_image_path">
      <img :src="item.food_image_path" alt="food" />
    </div>
    <div class="food-icon" v-else>
      <AppIcon name="diet" :size="20" />
    </div>
    <div class="info" @click="$emit('click', item)">
      <div class="desc ellipsis">{{ item.food_desc || '未命名食物' }}</div>
      <div class="meta">
        <span class="cal num">{{ Math.round(item.calorie || 0) }} kcal</span>
        <span v-if="item.protein" class="nutri num">蛋白 {{ Math.round(item.protein) }}g</span>
        <span v-if="item.input_type" class="tag">{{
          Number(item.input_type) === 2 ? '识别' : '手动'
        }}</span>
      </div>
    </div>
    <div class="actions">
      <button class="act" @click="$emit('edit', item)" aria-label="编辑">
        <AppIcon name="edit" :size="17" />
      </button>
      <button class="act del" @click="$emit('delete', item)" aria-label="删除">
        <AppIcon name="trash" :size="17" />
      </button>
    </div>
  </div>
</template>

<script setup>
import AppIcon from '@/components/icons/AppIcon.vue'

defineProps({
  item: { type: Object, required: true }
})
defineEmits(['click', 'edit', 'delete'])
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.diet-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid var(--border);

  &:last-child {
    border-bottom: none;
  }
}

.food-thumb,
.food-icon {
  width: 42px;
  height: 42px;
  border-radius: @r-md;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--surface-2);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--lime-ink);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.info {
  flex: 1;
  min-width: 0;

  .desc {
    font-size: 14px;
    color: var(--text-1);
    font-weight: 500;
  }
  .meta {
    margin-top: 3px;
    font-size: 12px;
    color: var(--text-3);
    display: flex;
    align-items: center;
    gap: 10px;

    .cal {
      color: var(--orange);
      font-weight: 600;
    }
    .tag {
      padding: 1px 7px;
      border-radius: 999px;
      border: 1px solid var(--border);
      color: var(--text-2);
      font-size: 11px;
      font-family: @font-mono;
    }
  }
}

.actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.act {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: @r-sm;
  background: transparent;
  color: var(--text-3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background @dur-fast @ease-out, color @dur-fast @ease-out;

  &:hover {
    background: var(--hover);
    color: var(--text-1);
  }
  &.del:hover {
    color: var(--red);
    background: var(--red-soft);
  }
}
</style>
