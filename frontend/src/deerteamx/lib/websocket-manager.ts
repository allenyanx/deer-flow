/**
 * DeerTeamX WebSocket 全局管理器（单例模式）
 * 对齐架构设计文档 4.5.3 节
 */

export class WebSocketManager {
  private static instance: WebSocketManager;
  private ws: WebSocket | null = null;
  private subscribers: Map<string, Set<(message: any) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = Infinity;
  private reconnectDelay = 1000;

  private constructor() {}

  static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager();
    }
    return WebSocketManager.instance;
  }

  /**
   * 建立 WebSocket 连接
   * 采用消息传递认证机制
   */
  connect(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8000/ws/global';
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        // 发送认证消息
        this.ws?.send(JSON.stringify({ type: 'auth', token }));
      };

      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === 'auth_result') {
          if (message.success) {
            this.reconnectAttempts = 0;
            resolve();
          } else {
            reject(new Error(message.reason || 'Authentication failed'));
          }
        } else {
          // 分发给订阅者
          const eventType = message.type;
          this.subscribers.get(eventType)?.forEach((cb) => cb(message));
        }
      };

      this.ws.onerror = () => {
        reject(new Error('WebSocket connection failed'));
      };

      this.ws.onclose = () => {
        // 指数退避重连
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts), 30000);
          this.reconnectAttempts++;
          setTimeout(() => this.connect(token), delay);
        }
      };
    });
  }

  /**
   * 订阅特定事件类型
   */
  subscribe(eventType: string, callback: (message: any) => void): () => void {
    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, new Set());
    }
    this.subscribers.get(eventType)!.add(callback);

    // 返回取消订阅函数
    return () => {
      this.subscribers.get(eventType)?.delete(callback);
    };
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.ws?.close();
    this.ws = null;
    this.subscribers.clear();
    this.reconnectAttempts = 0;
  }

  /**
   * 重新认证（Token 刷新时调用）
   */
  reauth(token: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'reauth', token }));
    }
  }
}
