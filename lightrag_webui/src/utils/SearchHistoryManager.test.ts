import { beforeEach, describe, expect, test } from 'bun:test'

import { SearchHistoryManager } from '@/utils/SearchHistoryManager'

describe('SearchHistoryManager.mergePopularLabels', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  test('keeps recent user searches and adds newly ingested popular labels', () => {
    SearchHistoryManager.addToHistory('浮点例外')
    SearchHistoryManager.mergePopularLabels([
      '浮点例外',
      '2号螺杆空压机',
      '排气压力不足'
    ])

    expect(SearchHistoryManager.getHistoryLabels()).toEqual([
      '浮点例外',
      '2号螺杆空压机',
      '排气压力不足'
    ])
    expect(
      SearchHistoryManager.getRecentSearches().map((item) => item.label)
    ).toEqual(['浮点例外'])
  })

  test('replaces stale recommendations while deduplicating the list', () => {
    SearchHistoryManager.mergePopularLabels(['旧标签', '旧标签', '新文件'])
    SearchHistoryManager.mergePopularLabels(['新文件', '新设备'])

    expect(SearchHistoryManager.getHistoryLabels()).toEqual(['新文件', '新设备'])
  })
})
