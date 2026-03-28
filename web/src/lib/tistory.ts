export async function postToTistory(post: {
  title: string;
  html_content: string;
  tags: string[];
}, blogName: string, visibility = 0) {
  const token = process.env.TISTORY_ACCESS_TOKEN!;

  const body = new URLSearchParams({
    access_token: token,
    output: "json",
    blogName,
    title: post.title,
    content: post.html_content,
    visibility: String(visibility),
    category: "0",
    tag: post.tags.join(","),
  });

  const res = await fetch("https://www.tistory.com/apis/post/write", {
    method: "POST",
    body,
  });

  const data = await res.json();
  if (data.tistory?.status !== "200") {
    throw new Error(`티스토리 발행 실패: ${JSON.stringify(data)}`);
  }

  return data.tistory.postId;
}

export function getBlogName(blogType: string): string {
  const name = blogType === "dev"
    ? process.env.TISTORY_BLOG_DEV || ""
    : process.env.TISTORY_BLOG_CPC || "";

  if (!name) throw new Error(`TISTORY_BLOG_${blogType === "dev" ? "DEV" : "CPC"} 설정 필요`);
  return name.replace(".tistory.com", "").trim();
}
