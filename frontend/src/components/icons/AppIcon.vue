<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="stroke"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="app-icon"
    v-html="inner"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 22 },
  stroke: { type: [Number, String], default: 1.8 }
})

const ICONS = {
  home: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v9a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-9"/><path d="M9.5 20v-5h5v5"/>',
  diet: '<path d="M3 11h18a8 8 0 0 1-16 0Z"/><path d="M9 4c0 1.4-1 2-1 3M13 4c0 1.4-1 2-1 3"/>',
  exercise:
    '<line x1="3" y1="9" x2="3" y2="15"/><line x1="21" y1="9" x2="21" y2="15"/><line x1="6.5" y1="10" x2="6.5" y2="14"/><line x1="17.5" y1="10" x2="17.5" y2="14"/><line x1="6.5" y1="12" x2="17.5" y2="12"/>',
  chart:
    '<line x1="4" y1="20" x2="20" y2="20"/><rect x="6" y="12" width="3" height="6" rx="1"/><rect x="11" y="7" width="3" height="11" rx="1"/><rect x="16" y="14" width="3" height="4" rx="1"/>',
  ai: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M18.5 3.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  logout:
    '<path d="M14 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4"/><path d="M14 12H5"/><path d="M9 8l-4 4 4 4"/>',
  menu: '<line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/>',
  collapse: '<path d="M13 6l-6 6 6 6"/><path d="M19 6l-6 6 6 6"/>',
  sun: '<circle cx="12" cy="12" r="4.2"/><line x1="12" y1="2.5" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="21.5"/><line x1="2.5" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="21.5" y2="12"/><line x1="5" y1="5" x2="6.8" y2="6.8"/><line x1="17.2" y1="17.2" x2="19" y2="19"/><line x1="19" y1="5" x2="17.2" y2="6.8"/><line x1="6.8" y1="17.2" x2="5" y2="19"/>',
  moon: '<path d="M21 13a9 9 0 1 1-9.4-9 7 7 0 0 0 9.4 9z"/>',
  // 品牌符号：碗形容器 + 内部同心思维纹理 + 右上智能指示点（与 favicon.svg 同源）
  logo:
    '<path d="M3.6 11.5 H20.4 A8.4 8.4 0 0 1 3.6 11.5 Z"/>' +
    '<path d="M15.9 11.5 A3.9 3.9 0 0 1 8.1 11.5" stroke-width="1.4"/>' +
    '<path d="M14.1 11.5 A2.1 2.1 0 0 1 9.9 11.5" stroke-width="1.4"/>' +
    '<circle cx="19.6" cy="5.2" r="1.5" fill="currentColor" stroke="none"/>',
  bell: '<path d="M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
  edit: '<path d="M4 20h4l10-10-4-4L4 16v4z"/><path d="M14 6l4 4"/>',
  trash:
    '<path d="M4 7h16"/><path d="M9.5 7V5a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v2"/><path d="M6.5 7l1 13a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1l1-13"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  camera:
    '<path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.2"/>',
  calendar:
    '<rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 9.5h17M8 3.5v3M16 3.5v3"/>',
  chevdown: '<path d="M6 9l6 6 6-6"/>',
  back: '<path d="M19 12H5"/><path d="M11 6l-6 6 6 6"/>',
  fire: '<path d="M12 3s5 4.2 5 9a5 5 0 0 1-10 0c0-2 1-3.6 2.2-4.6 0 1.6 1 2.6 2 2.6 0-3 1.2-5 0.8-7z"/>',
  drop: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.4"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 7.5v.2"/>',
  star: '<path d="M12 3l2.4 6.2L21 9.7l-5 4.4 1.6 6.4L12 17l-5.6 3.5L8 14.1 3 9.7l6.6-.5z"/>',
  medal: '<circle cx="12" cy="14.5" r="4.5"/><path d="M8.5 10.5L6 3h12l-2.5 7.5"/>',
  settings:
    '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2L14.3 3h-4l-.3 2.5a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12a7 7 0 0 0 .1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2L9.7 21h4l.3-2.5a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5A7 7 0 0 0 19 12z"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-3.6-3.6"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  bolt: '<path d="M13 3L5 13h6l-1 8 8-10h-6z"/>',
  refresh: '<path d="M20 11a8 8 0 1 0-1.6 5.2"/><path d="M20 4v6h-6"/>',
  send: '<path d="M4 12l16-8-6 16-3-6.5L4 12z"/>',
  chat: '<path d="M20 15a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
  mic: '<path d="M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z"/><path d="M5 11a7 7 0 0 0 14 0"/><line x1="12" y1="18" x2="12" y2="21"/><line x1="9" y1="21" x2="15" y2="21"/>'
}

const inner = computed(() => ICONS[props.name] || '')
</script>

<style scoped>
.app-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
