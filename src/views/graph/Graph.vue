<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Graph } from '@antv/g6'
import { get } from '@/api/client'
import type { GraphData, KGNode, KGEdge } from '@/types'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const containerRef = ref<HTMLDivElement | null>(null)
const loading = ref(true)
const selectedNode = ref<KGNode | null>(null)
const graphData = ref<GraphData | null>(null)
const zoomLevel = ref(1)
const activeTab = ref<'graph' | 'compare' | 'sankey'>('graph')
const showAllExamples = ref(false)
const searchQuery = ref('')
const selectedSources = ref<string[]>([])
const showSourceDropdown = ref(false)

const sankeyMockData = {
  nodes: [
    { id: 's1', name: '诊断学', type: 'source' },
    { id: 's2', name: '内科学', type: 'source' },
    { id: 's3', name: '生理学', type: 'source' },
    { id: 's4', name: '治疗学', type: 'source' },
    { id: 's5', name: '微生物学', type: 'source' },
    { id: 'c1', name: '心肌炎', type: 'concept' },
    { id: 'c2', name: '心包积液', type: 'concept' },
    { id: 'c3', name: '心力衰竭', type: 'concept' },
    { id: 'c4', name: '细菌感染', type: 'concept' },
    { id: 'f1', name: '心电图异常', type: 'fact' },
    { id: 'f2', name: '利尿剂治疗', type: 'fact' },
    { id: 'd1', name: '肌钙蛋白', type: 'definition' },
    { id: 'd2', name: '炎症反应', type: 'definition' },
  ],
  links: [
    { source: 's1', target: 'c1', value: 5 },
    { source: 's2', target: 'c1', value: 3 },
    { source: 's1', target: 'c2', value: 4 },
    { source: 's2', target: 'c3', value: 6 },
    { source: 's3', target: 'd2', value: 4 },
    { source: 's4', target: 'f2', value: 3 },
    { source: 's5', target: 'c4', value: 3 },
    { source: 's1', target: 'f1', value: 2 },
    { source: 's1', target: 'd1', value: 3 },
    { source: 's2', target: 'f1', value: 2 },
    { source: 's3', target: 'c1', value: 2 },
    { source: 's2', target: 'd1', value: 1 },
  ],
}

const mockCompression = {
  before: 150,
  after_dedup: 120,
  after_alignment: 42,
  surface_ratio: 0.80,
  semantic_ratio: 0.28,
}

const mockExamples = [
  { conceptA: '细胞呼吸（生理学）', conceptB: '呼吸作用（内科学）', mergedAs: '细胞呼吸/呼吸作用' },
  { conceptA: '心肌炎（内科学）', conceptB: '心肌炎症（诊断学）', mergedAs: '心肌炎' },
  { conceptA: '心音混浊', conceptB: '心音异常', mergedAs: '心音异常' },
  { conceptA: '炎症反应', conceptB: '炎性应答', mergedAs: '炎症反应' },
  { conceptA: 'ST段抬高', conceptB: 'ST段上升', mergedAs: 'ST段抬高' },
]

let graph: Graph | null = null

const mockGraphData: GraphData = {
  nodes: [
    { id: 'n1', label: '心肌炎', type: 'concept', description: '心肌炎症性疾病，可由感染、自身免疫等因素引起', source: '诊断学', frequency: 12 },
    { id: 'n2', label: '心包积液', type: 'concept', description: '心包腔内液体积聚', source: '诊断学', frequency: 8 },
    { id: 'n3', label: '心电图异常', type: 'fact', description: 'ST段抬高是典型表现', source: '内科学', frequency: 6 },
    { id: 'n4', label: '肌钙蛋白', type: 'definition', description: '心肌损伤标志物', source: '诊断学', frequency: 10 },
    { id: 'n5', label: '心力衰竭', type: 'concept', description: '心脏泵血功能障碍', source: '内科学', frequency: 15 },
    { id: 'n6', label: '利尿剂治疗', type: 'fact', description: '呋塞米是首选利尿剂', source: '治疗学', frequency: 5 },
    { id: 'n7', label: '炎症反应', type: 'definition', description: '机体对损伤的防御反应', source: '生理学', frequency: 9 },
    { id: 'n8', label: '细菌感染', type: 'concept', description: '细菌侵入组织引起感染', source: '微生物学', frequency: 7 },
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
  '诊断学': '#8b5cf6',
  '内科学': '#ec4899',
  '生理学': '#f97316',
  '治疗学': '#06b6d4',
  '微生物学': '#14b8a6',
}

function getNodeType(node: KGNode): string {
  const freq = node.frequency || 1
  if (freq >= 10) return 'high-freq'
  if (freq >= 6) return 'mid-freq'
  return 'low-freq'
}

function buildG6Data(data: GraphData) {
  const shapeMap: Record<string, string> = {
    concept: 'circle',
    fact: 'rect',
    definition: 'triangle',
  }

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
      shape: shapeMap[node.type] || 'circle',
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

const filteredGraphData = computed(() => {
  if (!graphData.value) return graphData.value
  const query = searchQuery.value.trim().toLowerCase()
  const sources = selectedSources.value
  const nodes = graphData.value.nodes.filter(n => {
    const matchQuery = !query || n.label.toLowerCase().includes(query) || n.description.toLowerCase().includes(query)
    const matchSource = sources.length === 0 || sources.includes(n.source)
    return matchQuery && matchSource
  })
  const nodeIds = new Set(nodes.map(n => n.id))
  const edges = graphData.value.edges.filter(e => nodeIds.has(e.from_node) && nodeIds.has(e.to_node))
  return { ...graphData.value, nodes, edges }
})

const allSources = computed(() => {
  if (!graphData.value) return []
  return [...new Set(graphData.value.nodes.map(n => n.source))].sort()
})

function toggleSource(source: string) {
  const idx = selectedSources.value.indexOf(source)
  if (idx >= 0) selectedSources.value.splice(idx, 1)
  else selectedSources.value.push(source)
}

function clearFilters() {
  searchQuery.value = ''
  selectedSources.value = []
}

const sankeyNodeHeight = 28
const sankeyNodeGap = 8
const sankeyLeftWidth = 120
const sankeyRightWidth = 120
const sankeyFlowWidth = 260

const sourceNodes = computed(() => sankeyMockData.nodes.filter(n => n.type === 'source'))
const targetNodes = computed(() => sankeyMockData.nodes.filter(n => n.type !== 'source'))

const totalSourceHeight = computed(() =>
  sourceNodes.value.length * sankeyNodeHeight + (sourceNodes.value.length - 1) * sankeyNodeGap
)
const totalTargetHeight = computed(() =>
  targetNodes.value.length * sankeyNodeHeight + (targetNodes.value.length - 1) * sankeyNodeGap
)

const sankeyChartHeight = computed(() =>
  Math.max(totalSourceHeight.value, totalTargetHeight.value) + 40
)

const sankeyNodePositions = computed(() => {
  const positions: Record<string, { x: number; y: number; width: number; height: number }> = {}
  const chartH = sankeyChartHeight.value
  const gap = 10

  const srcTotalH = totalSourceHeight.value
  const srcStartY = Math.max(0, (chartH - srcTotalH) / 2)
  sourceNodes.value.forEach((n, i) => {
    positions[n.id] = {
      x: gap,
      y: srcStartY + i * (sankeyNodeHeight + sankeyNodeGap),
      width: sankeyLeftWidth - gap,
      height: sankeyNodeHeight,
    }
  })

  const tgtTotalH = totalTargetHeight.value
  const tgtStartY = Math.max(0, (chartH - tgtTotalH) / 2)
  const rightX = gap + sankeyLeftWidth + sankeyFlowWidth
  targetNodes.value.forEach((n, i) => {
    positions[n.id] = {
      x: rightX,
      y: tgtStartY + i * (sankeyNodeHeight + sankeyNodeGap),
      width: sankeyRightWidth,
      height: sankeyNodeHeight,
    }
  })

  return positions
})

const sankeyLinks = computed(() => {
  const maxVal = Math.max(...sankeyMockData.links.map(l => l.value), 1)
  const positions = sankeyNodePositions.value
  return sankeyMockData.links.map(link => {
    const src = positions[link.source]
    const tgt = positions[link.target]
    if (!src || !tgt) return null
    const thickness = Math.max(3, (link.value / maxVal) * 10)
    const x1 = src.x + src.width
    const y1 = src.y + src.height / 2
    const x2 = tgt.x
    const y2 = tgt.y + tgt.height / 2
    const midX = x1 + (x2 - x1) / 2
    return {
      d: `M ${x1} ${y1 - thickness / 2} C ${midX} ${y1 - thickness / 2}, ${midX} ${y2 - thickness / 2}, ${x2} ${y2 - thickness / 2} L ${x2} ${y2 + thickness / 2} C ${midX} ${y2 + thickness / 2}, ${midX} ${y1 + thickness / 2}, ${x1} ${y1 + thickness / 2} Z`,
      thickness,
      source: link.source,
      target: link.target,
      value: link.value,
      targetNode: sankeyMockData.nodes.find(n => n.id === link.target),
    }
  }).filter((l): l is NonNullable<typeof l> => l !== null)
})

function initGraph() {
  if (!containerRef.value || !graphData.value) return

  const { nodes, edges } = buildG6Data(filteredGraphData.value || graphData.value)

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

watch([searchQuery, selectedSources], () => {
  if (graph && filteredGraphData.value) {
    const { nodes, edges } = buildG6Data(filteredGraphData.value)
    graph.setData({ nodes, edges })
    graph.render()
  }
})

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
          <div class="tab-switcher">
            <button class="tab-btn" :class="{ active: activeTab === 'graph' }" @click="activeTab = 'graph'">🕸️ 图谱</button>
            <button class="tab-btn" :class="{ active: activeTab === 'compare' }" @click="activeTab = 'compare'">📊 对比</button>
            <button class="tab-btn" :class="{ active: activeTab === 'sankey' }" @click="activeTab = 'sankey'">📈 流向</button>
          </div>
          <template v-if="activeTab === 'graph'">
            <div class="search-box">
              <input
                v-model="searchQuery"
                type="text"
                class="input search-input"
                placeholder="搜索节点..."
              />
              <div class="source-filter" @click.stop>
                <button class="btn btn-outline btn-sm source-filter-btn" @click="showSourceDropdown = !showSourceDropdown">
                  📚 来源{{ selectedSources.length > 0 ? ` (${selectedSources.length})` : '' }}
                </button>
                <div v-if="showSourceDropdown" class="source-dropdown">
                  <label v-for="src in allSources" :key="src" class="source-option">
                    <input type="checkbox" :checked="selectedSources.includes(src)" @change="toggleSource(src)" />
                    <span>{{ src }}</span>
                  </label>
                  <div v-if="selectedSources.length > 0" class="source-clear" @click="clearFilters">清除筛选</div>
                </div>
              </div>
            </div>
            <span class="zoom-badge">缩放: {{ Math.round(zoomLevel * 100) }}%</span>
            <div class="zoom-btns">
              <button class="btn btn-outline btn-sm" @click="handleZoomOut">−</button>
              <button class="btn btn-outline btn-sm" @click="handleZoomIn">+</button>
              <button class="btn btn-outline btn-sm" @click="handleFitView">适应</button>
            </div>
          </template>
        </div>
      </div>

      <div class="graph-main">
        <template v-if="activeTab === 'graph'">
          <LoadingSpinner v-if="loading" text="加载图谱中..." />
          <div v-show="!loading" ref="containerRef" class="graph-container" />
        </template>

        <template v-else-if="activeTab === 'compare'">
          <div class="compare-panel">
            <div class="compare-stat-bar">
              <span class="stat-main">整合前: <strong>{{ mockCompression.before }}</strong> 个节点 &rarr; 整合后: <strong>{{ mockCompression.after_alignment }}</strong> 个节点</span>
              <div class="stat-tags">
                <span class="stat-tag">压缩比: {{ Math.round(mockCompression.semantic_ratio * 100) }}%</span>
                <span class="stat-tag stat-tag-surface">表面匹配: 15</span>
                <span class="stat-tag stat-tag-semantic">语义匹配: 23</span>
              </div>
            </div>

            <div class="compression-bar-section">
              <div class="compression-label">压缩过程</div>
              <div class="compression-track">
                <div class="compression-step step-before">
                  <div class="step-value">{{ mockCompression.before }}</div>
                  <div class="step-label">原始</div>
                </div>
                <div class="compression-arrow">
                  <div class="arrow-line"></div>
                  <div class="arrow-label">去重</div>
                </div>
                <div class="compression-step step-dedup">
                  <div class="step-value">{{ mockCompression.after_dedup }}</div>
                  <div class="step-label">去重后</div>
                </div>
                <div class="compression-arrow">
                  <div class="arrow-line"></div>
                  <div class="arrow-label">对齐</div>
                </div>
                <div class="compression-step step-final">
                  <div class="step-value">{{ mockCompression.after_alignment }}</div>
                  <div class="step-label">对齐后</div>
                </div>
              </div>
            </div>

            <div class="examples-section">
              <div class="examples-header" @click="showAllExamples = !showAllExamples">
                <span class="examples-title">去重示例</span>
                <span class="examples-toggle">{{ showAllExamples ? '收起 ▲' : '展开 ▼' }}</span>
              </div>
              <transition name="expand">
                <ul v-if="showAllExamples" class="examples-list">
                  <li v-for="(ex, idx) in mockExamples" :key="idx" class="example-item">
                    <span class="ex-a">{{ ex.conceptA }}</span>
                    <span class="ex-equiv">&equiv;</span>
                    <span class="ex-b">{{ ex.conceptB }}</span>
                    <span class="ex-arrow">&rarr;</span>
                    <span class="ex-merged">{{ ex.mergedAs }}</span>
                  </li>
                </ul>
              </transition>
            </div>
          </div>
        </template>

        <template v-else-if="activeTab === 'sankey'">
          <div class="sankey-panel">
            <div class="sankey-title">教材 → 知识点 流向图</div>
            <div class="sankey-chart-container">
              <div class="sankey-header sankey-header-left">教材来源</div>
              <div class="sankey-header sankey-header-right">知识点</div>
              <svg class="sankey-svg" :width="sankeyLeftWidth + sankeyFlowWidth + sankeyRightWidth + 20" :height="sankeyChartHeight">
                <defs>
                  <linearGradient id="flowGradConcept" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#2563eb" stop-opacity="0.5" />
                    <stop offset="100%" stop-color="#2563eb" stop-opacity="0.2" />
                  </linearGradient>
                  <linearGradient id="flowGradFact" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#16a34a" stop-opacity="0.5" />
                    <stop offset="100%" stop-color="#16a34a" stop-opacity="0.2" />
                  </linearGradient>
                  <linearGradient id="flowGradDef" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#d97706" stop-opacity="0.5" />
                    <stop offset="100%" stop-color="#d97706" stop-opacity="0.2" />
                  </linearGradient>
                </defs>
                <path
                  v-for="(link, idx) in sankeyLinks"
                  :key="idx"
                  :d="link.d"
                  :fill="link.targetNode?.type === 'fact' ? 'url(#flowGradFact)' : link.targetNode?.type === 'definition' ? 'url(#flowGradDef)' : 'url(#flowGradConcept)'"
                  stroke="none"
                />
              </svg>
              <div class="sankey-nodes-layer" style="left:0; width:100%">
                <div
                  v-for="src in sourceNodes"
                  :key="src.id"
                  class="sankey-node source-node"
                  :style="{ top: sankeyNodePositions[src.id].y + 'px', left: sankeyNodePositions[src.id].x + 'px', width: sankeyNodePositions[src.id].width + 'px', height: sankeyNodeHeight + 'px' }"
                >
                  <span class="node-label">{{ src.name }}</span>
                  <span class="node-count">{{ sankeyMockData.links.filter(l => l.source === src.id).reduce((s, l) => s + l.value, 0) }}</span>
                </div>
                <div
                  v-for="tgt in targetNodes"
                  :key="tgt.id"
                  class="sankey-node"
                  :class="`${tgt.type}-node`"
                  :style="{ top: sankeyNodePositions[tgt.id].y + 'px', left: sankeyNodePositions[tgt.id].x + 'px', width: sankeyNodePositions[tgt.id].width + 'px', height: sankeyNodeHeight + 'px' }"
                >
                  <span class="node-label">{{ tgt.name }}</span>
                  <span class="node-count">{{ sankeyMockData.links.filter(l => l.target === tgt.id).reduce((s, l) => s + l.value, 0) }}</span>
                </div>
              </div>
            </div>
            <div class="sankey-legend">
              <span class="legend-item"><span class="legend-dot concept-bg" /> 概念</span>
              <span class="legend-item"><span class="legend-dot fact-bg" /> 事实</span>
              <span class="legend-item"><span class="legend-dot definition-bg" /> 定义</span>
            </div>
          </div>
        </template>

        <template v-if="activeTab === 'graph'">
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
          <div class="legend-item"><span class="legend-shape legend-shape-circle" style="background:#2563eb" /> 概念 · 圆形</div>
          <div class="legend-item"><span class="legend-shape legend-shape-rect" style="background:#16a34a" /> 事实 · 矩形</div>
          <div class="legend-item"><span class="legend-shape legend-shape-triangle" style="--triangle-color:#d97706" /> 定义 · 三角形</div>
          <div class="legend-divider" />
          <div class="legend-title">教材来源</div>
          <div v-for="(color, source) in sourceColorMap" :key="source" class="legend-item">
            <span class="legend-line" :style="{ background: color }" /> {{ source }}
          </div>
        </div>
      </template>
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

.legend-shape {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  display: inline-block;
}

.legend-shape-circle {
  border-radius: 50%;
}

.legend-shape-rect {
  border-radius: 2px;
}

.legend-shape-triangle {
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-bottom: 12px solid var(--triangle-color, #d97706);
  background: transparent !important;
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

.tab-switcher {
  display: flex;
  gap: 2px;
  background: var(--color-bg);
  border-radius: 6px;
  padding: 2px;
}

.tab-btn {
  border: none;
  background: transparent;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 4px;
  color: var(--color-text-secondary);
  transition: all var(--transition);
  position: relative;
}

.tab-btn:hover {
  color: var(--color-text);
}

.tab-btn.active {
  background: var(--color-surface);
  color: var(--color-primary);
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 2px;
  background: var(--color-primary);
  border-radius: 1px;
}

.compare-panel {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
  background: #fafbfc;
}

.compare-stat-bar {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px 20px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-main {
  font-size: 15px;
  font-weight: 500;
}

.stat-main strong {
  color: var(--color-primary);
  font-size: 18px;
}

.stat-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-tag {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.stat-tag-surface {
  background: #dbeafe;
  color: #2563eb;
}

.stat-tag-semantic {
  background: #fef3c7;
  color: #d97706;
}

.compression-bar-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 20px;
}

.compression-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--color-text);
}

.compression-track {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
}

.compression-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 20px;
  border-radius: var(--radius);
  min-width: 80px;
}

.step-before {
  background: #fee2e2;
  color: #dc2626;
}

.step-dedup {
  background: #fef3c7;
  color: #d97706;
}

.step-final {
  background: #dcfce7;
  color: #16a34a;
}

.step-value {
  font-size: 24px;
  font-weight: 700;
}

.step-label {
  font-size: 11px;
  font-weight: 500;
  opacity: 0.8;
}

.compression-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
}

.arrow-line {
  width: 40px;
  height: 2px;
  background: var(--color-border);
  position: relative;
}

.arrow-line::after {
  content: '';
  position: absolute;
  right: -4px;
  top: -3px;
  width: 0;
  height: 0;
  border-left: 6px solid var(--color-border);
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
}

.arrow-label {
  font-size: 10px;
  color: var(--color-text-secondary);
}

.examples-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}

.examples-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  transition: background var(--transition);
}

.examples-header:hover {
  background: var(--color-bg);
}

.examples-title {
  font-size: 13px;
  font-weight: 600;
}

.examples-toggle {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.examples-list {
  list-style: none;
  margin: 0;
  padding: 0 20px 16px;
}

.example-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border);
  font-size: 12px;
}

.example-item:last-child {
  border-bottom: none;
}

.ex-a {
  color: #dc2626;
  font-weight: 500;
  max-width: 35%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ex-equiv {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.ex-b {
  color: #d97706;
  font-weight: 500;
  max-width: 35%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ex-arrow {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.ex-merged {
  color: #16a34a;
  font-weight: 600;
  flex-shrink: 0;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
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

/* ===== 搜索框 + 来源筛选 ===== */
.search-box {
  display: flex;
  align-items: center;
  gap: 6px;
}

.search-input {
  width: 160px;
  padding: 4px 8px;
  font-size: 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  outline: none;
  transition: border-color var(--transition);
}

.search-input:focus {
  border-color: var(--color-primary);
}

.source-filter {
  position: relative;
}

.source-filter-btn {
  white-space: nowrap;
  font-size: 12px;
}

.source-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  min-width: 160px;
  padding: 8px;
}

.source-option {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
}

.source-option:hover {
  background: var(--color-bg);
}

.source-clear {
  margin-top: 4px;
  padding: 4px 6px;
  font-size: 11px;
  color: var(--color-danger);
  cursor: pointer;
  text-align: center;
  border-top: 1px solid var(--color-border);
}

.source-clear:hover {
  text-decoration: underline;
}

/* ===== 桑基图 ===== */
.sankey-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow-y: auto;
}

.sankey-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 16px;
}

.sankey-chart-container {
  position: relative;
  width: 520px;
  margin: 0 auto;
}

.sankey-header {
  position: absolute;
  top: -20px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-align: center;
  z-index: 2;
}

.sankey-header-left {
  left: 10px;
  width: 110px;
}

.sankey-header-right {
  left: 390px;
  width: 120px;
}

.sankey-svg {
  display: block;
  overflow: visible;
}

.sankey-nodes-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
}

.sankey-node {
  position: absolute;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  font-size: 11px;
  border-radius: 6px;
  background: #f1f5f9;
  border: 1px solid var(--color-border);
  box-sizing: border-box;
}

.node-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.source-node {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: var(--color-primary);
  font-weight: 600;
}

.concept-node {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1e40af;
}

.fact-node {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #166534;
}

.definition-node {
  background: #fffbeb;
  border-color: #fde68a;
  color: #92400e;
}

.node-count {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 5px;
  border-radius: 8px;
  flex-shrink: 0;
  margin-left: 6px;
}

.sankey-legend {
  display: flex;
  gap: 16px;
  margin-top: 16px;
  justify-content: center;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.concept-bg { background: #2563eb; }
.fact-bg { background: #16a34a; }
.definition-bg { background: #d97706; }
</style>
