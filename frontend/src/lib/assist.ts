export const providerLabel = { anthropic: 'Claude', openai: 'OpenAI', google: 'Gemini' };
export function authorLabel(author: string): string {
  if (!author.startsWith('llm:')) return author;
  const [provider, ...model] = author.slice(4).split('/');
  return `글쓰기 보조(${providerLabel[provider as keyof typeof providerLabel] || provider} · ${model.join('/')})`;
}
