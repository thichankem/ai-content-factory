export interface ScriptBriefSettings {
  // 1. Chủ đề & góc nhìn
  topic: string;
  uniqueAngle: string;

  // 2. Nền tảng & định dạng
  platform: "tiktok" | "shorts" | "reels" | "youtube_long";
  targetDuration: string;
  aspectRatio: "9:16" | "16:9" | "1:1" | "4:5";
  customDurationSeconds?: number;

  // 3. Đối tượng khán giả
  audienceAgeGender: string;
  audienceKnowledge: string;
  audiencePainPoint: string;
  audienceDesire: string;

  // 4. Mục tiêu video
  videoGoal: "entertainment" | "education" | "conversion" | "follow" | "viral_debate";
  callToAction: string;

  // 5. Giọng điệu & phong cách
  tone: "humorous" | "serious" | "inspiring" | "dramatic" | "casual" | "provocative";
  includeMemeSlang: boolean;
  slangKeywords: string;

  // 6. Cấu trúc mong muốn
  hookType: "curiosity_gap" | "shocking_stat" | "fatal_mistake" | "counter_intuitive" | "story_teaser";
  structurePacing: "hook_body_climax_cta" | "problem_agitate_solution" | "myth_busting" | "3_step_tutorial";
  includeVisualCues: boolean;

  // 7. Nhân vật/hình thức thể hiện
  formatType: "talking_head" | "voiceover_broll" | "two_person_dialogue" | "cinematic_storytelling" | "pov_demo";

  // 8. Thông tin/dữ liệu cụ thể cần đưa vào (chống AI bịa)
  specificFactsAndData: string;
  referenceLinksAndDocs: string;
  uploadedFiles?: Array<{ name: string; size: number; snippet?: string }>;

  // 9. Ví dụ tham khảo
  benchmarkCreatorOrChannel: string;
  benchmarkScriptExample: string;
  benchmarkMediaUrl: string;
  uploadedVideoRef?: { name: string; extractedScript?: string };

  // 10. Điều cần tránh
  negativeConstraints: string;
  forbiddenWords: string;
}

export interface TargetScope {
  type: "full" | "selection" | "lines" | "section";
  startLine: number;
  endLine: number;
  selectedText: string;
  sectionTitle?: string;
  wordCount: number;
  estimatedSeconds: number;
}

export interface SpeechPacingConfig {
  wpm: number;
  label: string;
  preset: "slow" | "normal" | "fast" | "hyper" | "custom";
}

export interface ChatbotMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  targetScope?: TargetScope;
  diffBefore?: string;
  diffAfter?: string;
  applied?: boolean;
  canUndo?: boolean;
  timestamp: string;
}
