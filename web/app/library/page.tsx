import { listLibraryAssets } from "@/lib/api";
import { LibraryManager } from "@/components/LibraryManager";

export const dynamic = "force-dynamic";

async function loadLibraryAssets() {
  try {
    return await listLibraryAssets();
  } catch {
    return [];
  }
}

export default async function LibraryPage() {
  const assets = await loadLibraryAssets();

  return (
    <main className="page-shell">
      <section className="content-panel">
        <p className="eyebrow">Library</p>
        <h1 className="card-title">자료 라이브러리</h1>
        <p className="page-copy">
          카테고리 지정 업로드와 자료 목록 확인을 여기서 처리합니다. 프로젝트 연결은 개별
          프로젝트 화면에서 관리합니다.
        </p>
      </section>
      <LibraryManager initialAssets={assets} />
    </main>
  );
}
