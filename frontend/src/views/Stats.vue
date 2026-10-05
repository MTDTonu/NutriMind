<template>
  <div class="page stats-page">
    <NavBar title="数据统计" />

    <!-- 统计面板（组件化：与首页移动端区块共用同一份实现） -->
    <StatsPanel />
  </div>
</template>

<script setup>
import NavBar from '@/components/NavBar.vue'
import StatsPanel from '@/components/StatsPanel.vue'
</script>

<style lang="less" scoped>
@import '../styles/variable.less';

.stats-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
