/**
 * API配置文件
 * 包含API基础URL和AI问答功能所需的API参数
 */

// API基础URL配置
export const apiConfig = {
  // 后端API基础URL
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
}

export const aiChatConfig = {
  // OpenAI API地址
  apiEndpoint: 'https://api.deepseek.com/chat/completions',
  
  // 通过页面配置个人密钥，不将共享密钥打包进静态资源。
  apiKey: '',
  
  // 使用的模型
  model: 'deepseek-v4-flash '
}
