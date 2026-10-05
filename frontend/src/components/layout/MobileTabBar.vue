<template>
  <nav class="mtab">
    <router-link
      v-for="t in mobileTabs"
      :key="t.name"
      :to="{ name: t.name }"
      class="mtab-item"
      :class="{ active: route.name === t.name }"
    >
      <span class="tick" />
      <span class="mtab-ico"><AppIcon :name="t.icon" :size="22" /></span>
      <span class="mtab-label">{{ t.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'
import { mobileTabs } from '@/config/nav'

const route = useRoute()
</script>

<style lang="less" scoped>
@import '../../styles/variable.less';

.mtab {
  // 作为移动壳层的 flex 流内兄弟（而非 fixed 覆盖层）：
  // 这样内容区(.app-content-m)的高度会自动停在 Tab 栏上方，
  // flush 页(AI)的输入栏不会再被固定 Tab 栏压住/重叠。
  flex-shrink: 0;
  height: calc(60px + env(safe-area-inset-bottom));
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--topbar-bg);
  backdrop-filter: saturate(140%) blur(14px);
  -webkit-backdrop-filter: saturate(140%) blur(14px);
  border-top: 1px solid var(--border);
  display: flex;
}

.mtab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  color: var(--tabbar-text);
  transition: color @dur-fast @ease-out;
  position: relative;

  .tick {
    position: absolute;
    top: 0;
    width: 26px;
    height: 2px;
    border-radius: 0 0 3px 3px;
    background: transparent;
    transition: background @dur-fast @ease-out;
  }
  .mtab-ico {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 24px;
    transition: transform @dur-fast @ease-out;
  }
  .mtab-label {
    font-size: 10.5px;
    letter-spacing: 0.02em;
    line-height: 1;
  }

  &.active {
    color: var(--tabbar-active);
    .tick {
      background: var(--lime);
      box-shadow: var(--glow-lime);
    }
    .mtab-ico {
      transform: translateY(-1px);
    }
  }
}
</style>
