<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Graph } from '@antv/g6'
import { get } from '@/api/client'
import type { GraphData, KGNode, KGEdge } from '@/types'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const containerRef = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const selectedNode = ref<KGNode | null>(null)
const graphData = ref<GraphData | null>(null)
const zoomLevel = ref(1)

let graph: Graph | null = null

const mockGraphData: GraphData = {
  nodes: [
    { id: 'n1', label: '心肌炎', type: 'concept', description: '心肌炎症性疾病，可由感染、自身免疫等因素引起', source: '兽医诊断学', frequency: 12 },
    { id: 'n2', label: '心包积液', type: 'concept', description: '心包腔内液体积聚', source: '兽医诊断学', frequency: 8 },
    { id: 'n3', label: '心电图异常', type: 'fact', description: 'ST段抬高是典型表现', source: '兽医内科学', frequency: 6 },
    { id: 'n4', label: '肌钙蛋白', type: 'definition', description: '心肌损伤标志物', source: '兽医诊断学', frequency: 10 },
    { id: 'n5', label: '心力衰竭', type: 'concept', description: '心脏泵血功能障碍', source: '兽医内科学', frequency: 15 },
    { id: 'n6', label: '利尿剂治疗', type: 'fact', description: '呋塞米是首选利尿剂', source: '兽医治疗学', frequency: 5 },
    { id: 'n7', label: '炎症反应', type: 'definition', description: '机体对损伤的防御反应', source: '兽医生理学', frequency: 9 },
    { id: 'n8', label: '细菌感染', type: 'concept', description: '细菌侵入组织引起感染', source: '兽医微生物学', frequency: 7 },
  ],
  edges: [
    { from_node: 'n1', to_node: 'n2', relation_type: 'associate', weight: 0.8 },
    { from_node: 'n1', to_node: 'n3', relation_type: 'prerequisite', weight: 0.9 },
    { from_node: 'n1', to_node: 'n4', relation_type: 'prerequisite', weight: 0.85 },
    { from_node: 'n1', to_node: 'n5', relation_type: 'associate', weight: 0.7 },
    { from_node: 'n1', to_node: 'n7', relation_type: 'contains', weight: 0.95 },
    { from_node: 'n5', to_node: 'n6', relation_type: 'prerequisite', weight: 0.75 },
    { from_node: 'n8', to_node: 'n7', relation_type: 'prerequisite', weight: 0.8 },
    { from_node: 'n8', to_node: 'n1', relation_type: 'associate', weight: 0.6 },
  ],
  total_nodes: 8,
  total_edges: 8
}

const typeColorMap: Record<string, string> = {
  concept: '#2563eb',
  fact: '#16a34a',
  definition: '#d97706',
}

const sourceColorMap: Record<string, string> = {
  '兽医诊断学': '#8b5cf6',
  '兽医内科学': '#ec4899',
  '兽医生理学': '#f97316',
  '兽医治疗学': '#06b6d4',
  '兽医微生物学': '#14b8a6',
}

function getNodeType(node: KGNode): string {
  const freq = node.frequency || 1
  if (freq >= 10) return 'high-freq'
  if (freq >= 6) return 'mid-freq'
  return 'low-freq'
}

function buildG6Data(data: GraphData) {
  const nodes = data.nodes.map(node => ({
    id: node.id,
    label: node.label,
    type: getNodeType(node),
    data: node as unknown as Record<string, unknown>,
    style: {
      fill: typeColorMap[node.type] || '#64748b',
      stroke: sourceColorMap[node.source] || '#94a3b8',
      lineWidth: 2,
      r: 20 + (node.frequency || 1) * 2,
    },
  }))

  const edges = data.edges.map(edge => ({
    source: edge.from_node,
    target: edge.to_node,
    label: edge.relation_type === 'prerequisite' ? '前置' : edge.relation_type === 'contains' ? '包含' : '关联',
    style: {
      stroke: edge.relation_type === 'associate' ? '#94a3b8' : '#64748b',
      lineWidth: Math.max(1, edge.weight * 2),
      lineDash: edge.relation_type === 'associate' ? [4, 4] : undefined,
      endArrow: true,
    },
  }))

  return { nodes, edges }
}

function initGraph() {
  if (!containerRef.value || !graphData.value) return

  const { nodes, edges } = buildG6Data(graphData.value)

  graph = new Graph({
    container: containerRef.value,
    width: containerRef.value.clientWidth,
    height: containerRef.value.clientHeight,
    autoFit: 'view',
    layout: {
      type: 'force',
      preventOverlap: true,
      nodeSize: 40,
      linkDistance: 120,
      nodeStrength: -300,
      edgeStrength: 0.2,
      collide: true,
    },
    plugins: [
      {
        type: 'legend',
        position: 'top-right',
        padding: [8, 12, 8, 12],
        background: {
          padding: [4, 8, 4, 4],
          radius: 4,
          fill: '#ffffff',
          stroke: '#e2e8f0',
        },
      },
      {
        type: 'zoom-bar',
        position: 'bottom-left',
      },
    ],
    node: {
      style: {
        labelText: (d: any) => d.label,
        labelFill: '#ffffff',
        labelFontSize: 10,
        labelFontWeight: 500,
        lineWidth: 2,
      },
      state: {
        active: {
          strokeWidth: 3,
          shadowColor: '#2563eb',
          shadowBlur: 12,
        },
        selected: {
          strokeWidth: 3,
          stroke: '#f59e0b',
          shadowColor: '#f59e0b',
          shadowBlur: 12,
        },
      },
    },
    edge: {
      style: {
        labelText: (d: any) => d.label,
        labelFill: '#94a3b8',
        labelFontSize: 9,
        labelBackground: true,
        labelBackgroundFill: '#ffffff',
        labelBackgroundOpacity: 0.8,
        endArrow: true,
        endArrowSize: 6,
      },
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-node', 'click-select'],
  })

  graph.setData({ nodes, edges })

  graph.on('node:click', (e: any) => {
    const nodeId = e.target?.id
    const nodeData = graphData.value?.nodes.find(n => n.id === nodeId)
    selectedNode.value = nodeData || null
  })

  graph.on('canvas:click', () => {
    selectedNode.value = null
  })

  graph.on('viewportchange', (e: any) => {
    if (e.zoom) zoomLevel.value = Math.round(e.zoom * 100) / 100
  })

  graph.render()
}

function handleZoomIn() {
  if (!graph) return
  const zoom = graph.getZoom()
  graph.zoomTo(zoom * 1.2)
}

function handleZoomOut() {
  if (!graph) return
  const zoom = graph.getZoom()
  graph.zoomTo(zoom / 1.2)
}

function handleFitView() {
  graph?.fitView()
}

async function fetchGraph() {
  loading.value = true
  try {
    graphData.value = await get<GraphData>('/graph')
  } catch {
    graphData.value = mockGraphData
  } finally {
    loading.value = false
  }
}

let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  await fetchGraph()
  initGraph()
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      if (graph && containerRef.value) {
        graph.resize(containerRef.value.clientWidth, containerRef.value.clientHeight)
      }
    })
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
  graph?.destroy()
})
</script>

<template>
  <div class="graph-view">
    <div class="graph-toolbar">
      <span class="graph-title">知识图谱</span>
      <div class="toolbar-info">
        <span class="zoom-badge">缩放: {{ Math.round(zoomLevel * 100) }}%</span>
        <div class="zoom-btns">
          <button class="btn btn-outline btn-sm" @click="handleZoomOut">−</button>
          <button class="btn btn-outline btn-sm" @click="handleZoomIn">+</button>
          <button class="btn btn-outline btn-sm" @click="handleFitView">适应</button>
        </div>
      </div>
    </div>

    <div class="graph-main">
      <LoadingSpinner v-if="loading" text="加载图谱中..." />
      <div v-show="!loading" ref="containerRef" class="graph-container" />

      <transition name="slide">
        <div v-if="selectedNode" class="node-detail-panel">
          <div class="detail-header">
            <span class="detail-type-badge" :style="{ background: typeColorMap[selectedNode.type] }">
              {{ selectedNode.type === 'concept' ? '概念' : selectedNode.type === 'fact' ? '事实' : '定义' }}
            </span>
            <button class="detail-close" @click="selectedNode = null">✕</button>
          </div>
          <div class="detail-title">{{ selectedNode.label }}</div>
          <div class="detail-desc">{{ selectedNode.description }}</div>
          <div class="detail-meta">
            <span class="meta-item">📚 {{ selectedNode.source }}</span>
            <span class="meta-item">📊 频次: {{ selectedNode.frequency }}</span>
          </div>
        </div>
      </transition>

      <div class="graph-legend">
        <div class="legend-title">节点类型</div>
        <div class="legend-item"><span class="legend-dot" style="background:#2563eb" /> 概念</div>
        <div class="legend-item"><span class="legend-dot" style="background:#16a34a" /> 事实</div>
        <div class="legend-item"><span class="legend-dot" style="background:#d97706" /> 定义</div>
        <div class="legend-divider" />
        <div class="legend-title">教材来源</div>
        <div v-for="(color, source) in sourceColorMap" :key="source" class="legend-item">
          <span class="legend-line" :style="{ background: color }" /> {{ source }}
        </div>
      </div>
    </div>

    <div v-if="graphData" class="graph-footer">
      <span class="footer-stat">节点: {{ graphData.total_nodes }}</span>
      <span class="footer-stat">边: {{ graphData.total_edges }}</span>
    </div>
  </div>
</template>

<style scoped>
.graph-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-surface);
}

.graph-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.graph-title {
  font-size: 14px;
  font-weight: 600;
}

.toolbar-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zoom-badge {
  font-size: 11px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 2px 8px;
  border-radius: 10px;
}

.zoom-btns {
  display: flex;
  gap: 4px;
}

.graph-main {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.graph-container {
  width: 100%;
  height: 100%;
  background: #fafbfc;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all var(--transition);
  padding: 4px 10px;
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-text);
}

.btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.btn-sm {
  padding: 2px 8px;
  font-size: 12px;
  min-width: 28px;
}

.node-detail-panel {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 260px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
  box-shadow: var(--shadow-lg);
  z-index: 10;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.detail-type-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  color: white;
  font-weight: 500;
}

.detail-close {
  background: none;
  border: none;
  font-size: 14px;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 2px 4px;
  line-height: 1;
}

.detail-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.detail-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 12px;
}

.detail-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.graph-legend {
  position: absolute;
  top: 16px;
  left: 16px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px;
  font-size: 11px;
  z-index: 10;
  min-width: 140px;
}

.legend-title {
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-line {
  width: 16px;
  height: 3px;
  border-radius: 2px;
  flex-shrink: 0;
}

.legend-divider {
  height: 1px;
  background: var(--color-border);
  margin: 8px 0;
}

.graph-footer {
  display: flex;
  gap: 16px;
  padding: 6px 16px;
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}

.footer-stat {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.2s ease;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
