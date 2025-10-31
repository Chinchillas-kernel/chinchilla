#!/usr/bin/env python3
"""
LangGraph 워크플로우를 Mermaid 다이어그램으로 시각화
"""
import sys
from pathlib import Path
import webbrowser

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

from agent.router_runtime import get_runtime


def visualize_and_preview():
    """Mermaid 생성 + HTML로 브라우저에서 자동 미리보기"""
    print("=" * 70)
    print("워크플로우 시각화")
    print("=" * 70 + "\n")

    # 1. 그래프 생성
    graphs, hooks = get_runtime()
    first_category = list(graphs.keys())[0]
    common_graph = graphs[first_category]

    mermaid_code = common_graph.get_graph().draw_mermaid()

    # 2. Markdown 파일 저장
    md_file = project_root / "claudedocs" / "workflow_common.md"
    md_file.parent.mkdir(exist_ok=True)

    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# Common Workflow Structure\n\n")
        f.write("```mermaid\n")
        f.write(mermaid_code)
        f.write("\n```\n")

    print(f"Markdown 파일: {md_file}")

    # 3. HTML 파일 생성 및 브라우저 자동 열기
    html_file = project_root / "claudedocs" / "workflow_common.html"

    html_content = f"""<!DOCTYPE html>
  <html>
  <head>
      <meta charset="UTF-8">
      <title>Workflow Diagram</title>
      <script type="module">
          import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
          mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
      </script>
      <style>
          body {{ 
              font-family: Arial, sans-serif; 
              max-width: 1200px; 
              margin: 40px auto; 
              padding: 20px;
          }}
          h1 {{ color: #333; }}
          .mermaid {{ 
              background: #f5f5f5; 
              padding: 20px; 
              border-radius: 8px;
              margin: 20px 0;
          }}
      </style>
  </head>
  <body>
      <h1>Common Workflow Structure (All Categories)</h1>
      <p>모든 카테고리(news, legal, jobs, welfare)가 공유하는 그래프 구조입니다.</p>
      <div class="mermaid">
  {mermaid_code}
      </div>
  </body>
  </html>"""

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"HTML 파일: {html_file}")
    print(f"\n브라우저에서 여는 중...\n")

    # 4. 브라우저 자동 열기
    webbrowser.open(f"file://{html_file.absolute()}")

    print("=" * 70)
    print(" 완료!")
    print("=" * 70)
    print("\n 브라우저에서 다이어그램을 확인하세요!")
    print(f"   파일 경로: {html_file.absolute()}\n")


if __name__ == "__main__":
    visualize_and_preview()
