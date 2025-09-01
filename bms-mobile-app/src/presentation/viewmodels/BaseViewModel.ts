import { observable, action, makeObservable } from 'mobx';

/**
 * ViewModel 狀態枚舉
 */
export enum ViewModelState {
  IDLE = 'idle',
  LOADING = 'loading',
  SUCCESS = 'success',
  ERROR = 'error'
}

/**
 * ViewModel 基類
 * 提供通用的狀態管理和錯誤處理功能
 */
export abstract class BaseViewModel {
  @observable state: ViewModelState = ViewModelState.IDLE;
  @observable error: string | null = null;
  @observable isLoading: boolean = false;

  constructor() {
    makeObservable(this);
  }

  /**
   * 設置載入狀態
   */
  @action
  protected setLoading(loading: boolean): void {
    this.isLoading = loading;
    this.state = loading ? ViewModelState.LOADING : ViewModelState.IDLE;
    
    if (loading) {
      this.error = null; // 清除之前的錯誤
    }
  }

  /**
   * 設置成功狀態
   */
  @action
  protected setSuccess(): void {
    this.state = ViewModelState.SUCCESS;
    this.isLoading = false;
    this.error = null;
  }

  /**
   * 設置錯誤狀態
   */
  @action
  protected setError(error: string): void {
    this.state = ViewModelState.ERROR;
    this.isLoading = false;
    this.error = error;
    console.error(`❌ ViewModel 錯誤: ${error}`);
  }

  /**
   * 清除錯誤狀態
   */
  @action
  clearError(): void {
    this.error = null;
    if (this.state === ViewModelState.ERROR) {
      this.state = ViewModelState.IDLE;
    }
  }

  /**
   * 安全執行異步操作的包裝器
   * 自動處理載入狀態和錯誤捕獲
   */
  protected async executeAsync<T>(
    operation: () => Promise<T>,
    errorMessage: string = '操作失敗'
  ): Promise<T | null> {
    try {
      this.setLoading(true);
      const result = await operation();
      this.setSuccess();
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.setError(`${errorMessage}: ${message}`);
      return null;
    }
  }

  /**
   * 重試上次失敗的操作
   * 子類應該覆寫此方法以實現具體的重試邏輯
   */
  abstract retry(): Promise<void>;

  /**
   * 清理資源
   * 子類應該覆寫此方法以清理訂閱、定時器等資源
   */
  dispose(): void {
    // 基類暫時不需要清理任何資源
    console.log('🧹 ViewModel 資源清理完成');
  }

  /**
   * 獲取當前是否有錯誤
   */
  get hasError(): boolean {
    return this.error !== null;
  }

  /**
   * 獲取當前是否為成功狀態
   */
  get isSuccess(): boolean {
    return this.state === ViewModelState.SUCCESS;
  }

  /**
   * 獲取當前是否為空閒狀態
   */
  get isIdle(): boolean {
    return this.state === ViewModelState.IDLE;
  }
}