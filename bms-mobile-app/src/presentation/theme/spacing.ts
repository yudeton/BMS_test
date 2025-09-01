/**
 * 間距配置系統
 * 提供一致的間距值和佈局工具
 */

/**
 * 基礎間距單位 (8px 網格系統)
 */
const BASE_SPACING = 8;

/**
 * 間距大小配置
 */
export const spacing = {
  // 極小間距
  xs: BASE_SPACING * 0.5,     // 4px
  
  // 小間距
  sm: BASE_SPACING,           // 8px
  
  // 中等間距
  md: BASE_SPACING * 2,       // 16px
  
  // 大間距
  lg: BASE_SPACING * 3,       // 24px
  
  // 特大間距
  xl: BASE_SPACING * 4,       // 32px
  
  // 超大間距
  xxl: BASE_SPACING * 6,      // 48px
  
  // 巨大間距
  xxxl: BASE_SPACING * 8,     // 64px
} as const;

/**
 * 邊框圓角配置
 */
export const borderRadius = {
  // 無圓角
  none: 0,
  
  // 小圓角
  sm: 4,
  
  // 中等圓角
  md: 8,
  
  // 大圓角
  lg: 12,
  
  // 超大圓角
  xl: 16,
  
  // 圓形
  full: 999,
} as const;

/**
 * 陰影配置
 */
export const shadows = {
  // 無陰影
  none: {
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  
  // 小陰影
  sm: {
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 2,
  },
  
  // 中等陰影
  md: {
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 4,
  },
  
  // 大陰影
  lg: {
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  
  // 超大陰影
  xl: {
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 16,
  },
} as const;

/**
 * 邊框寬度配置
 */
export const borderWidth = {
  none: 0,
  thin: 1,
  medium: 2,
  thick: 4,
} as const;

/**
 * 佈局工具函數
 */
export const layout = {
  /**
   * 創建統一的 padding
   * @param size 間距大小
   */
  padding: (size: keyof typeof spacing) => ({
    padding: spacing[size],
  }),
  
  /**
   * 創建水平 padding
   * @param size 間距大小
   */
  paddingHorizontal: (size: keyof typeof spacing) => ({
    paddingHorizontal: spacing[size],
  }),
  
  /**
   * 創建垂直 padding
   * @param size 間距大小
   */
  paddingVertical: (size: keyof typeof spacing) => ({
    paddingVertical: spacing[size],
  }),
  
  /**
   * 創建統一的 margin
   * @param size 間距大小
   */
  margin: (size: keyof typeof spacing) => ({
    margin: spacing[size],
  }),
  
  /**
   * 創建水平 margin
   * @param size 間距大小
   */
  marginHorizontal: (size: keyof typeof spacing) => ({
    marginHorizontal: spacing[size],
  }),
  
  /**
   * 創建垂直 margin
   * @param size 間距大小
   */
  marginVertical: (size: keyof typeof spacing) => ({
    marginVertical: spacing[size],
  }),
  
  /**
   * 創建圓角樣式
   * @param size 圓角大小
   */
  borderRadius: (size: keyof typeof borderRadius) => ({
    borderRadius: borderRadius[size],
  }),
  
  /**
   * 創建陰影樣式
   * @param size 陰影大小
   * @param color 陰影顏色
   */
  shadow: (size: keyof typeof shadows, color = '#000000') => ({
    ...shadows[size],
    shadowColor: color,
  }),
  
  /**
   * 創建邊框樣式
   * @param width 邊框寬度
   * @param color 邊框顏色
   */
  border: (width: keyof typeof borderWidth, color: string) => ({
    borderWidth: borderWidth[width],
    borderColor: color,
  }),
  
  /**
   * 創建水平居中樣式
   */
  centerHorizontal: {
    alignItems: 'center' as const,
  },
  
  /**
   * 創建垂直居中樣式
   */
  centerVertical: {
    justifyContent: 'center' as const,
  },
  
  /**
   * 創建完全居中樣式
   */
  center: {
    alignItems: 'center' as const,
    justifyContent: 'center' as const,
  },
  
  /**
   * 創建 flex 填充樣式
   */
  flex: (value: number = 1) => ({
    flex: value,
  }),
  
  /**
   * 創建行佈局樣式
   */
  row: {
    flexDirection: 'row' as const,
  },
  
  /**
   * 創建列佈局樣式
   */
  column: {
    flexDirection: 'column' as const,
  },
  
  /**
   * 創建元素間隔樣式
   */
  spaceBetween: {
    justifyContent: 'space-between' as const,
  },
  
  /**
   * 創建元素周圍間隔樣式
   */
  spaceAround: {
    justifyContent: 'space-around' as const,
  },
  
  /**
   * 創建元素均分間隔樣式
   */
  spaceEvenly: {
    justifyContent: 'space-evenly' as const,
  },
};