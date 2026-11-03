import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  ApiError,
  type Design,
  type DesignParams,
  type Estimate,
  type FieldKey,
  type Material,
  type RequestDetail,
  type RequestSummary,
} from "./api";
import { DesignPanel } from "./components/DesignPanel";
import { EstimatePanel } from "./components/EstimatePanel";
import { Intake } from "./components/Intake";
import { RequestList } from "./components/RequestList";
import { StatusSteps } from "./components/StatusSteps";

export function App() {
  const [items, setItems] = useState<RequestSummary[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [design, setDesign] = useState<Design | null>(null);
  const [estimate, setEstimate] = useState<Estimate | null>(null);
  const [designProblems, setDesignProblems] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Какая заявка открыта сейчас. Ответы по другой заявке отбрасываются (R-04 ревью).
  const current = useRef<number | null>(null);

  const refreshList = useCallback(async () => setItems(await api.listRequests()), []);

  useEffect(() => {
    api.materials().then(setMaterials, () => setError("Сервер недоступен"));
    api.listRequests().then(setItems, () => setError("Сервер недоступен"));
  }, []);

  const load = useCallback(async (id: number | null) => {
    setDesignProblems([]);
    setError(null);
    current.current = id;
    // Сразу убираем данные прежней заявки: иначе форма конструкции успеет
    // инициализироваться чужими размерами (R-02 ревью).
    setRequest(null);
    setDesign(null);
    setEstimate(null);
    if (id === null) return;
    const [req, d, est] = await Promise.all([
      api.getRequest(id),
      api.getDesign(id).catch(() => null),
      api.getEstimate(id).catch(() => null),
    ]);
    if (current.current !== id) return;
    setRequest(req);
    setDesign(d);
    setEstimate(est);
  }, []);

  /** Применить ответ, только если пользователь не переключился на другую заявку. */
  const stillOpen = (id: number) => current.current === id;

  async function guarded(fn: () => Promise<void>) {
    setError(null);
    try {
      await fn();
    } catch (e) {
      if (e instanceof ApiError) {
        setError([e.message, ...e.problems].join(". "));
      } else {
        setError("Сервер недоступен");
      }
    }
  }

  function select(id: number | null) {
    setSelectedId(id);
    void guarded(() => load(id));
  }

  const onCreate = (text: string) =>
    guarded(async () => {
      const req = await api.createRequest(text);
      current.current = req.id;
      setSelectedId(req.id);
      setRequest(req);
      setDesign(null);
      setEstimate(null);
      await refreshList();
    });

  const onSaveField = (key: FieldKey, value: string) =>
    guarded(async () => {
      if (!request) return;
      const updated = await api.updateField(request.id, key, value);
      if (stillOpen(request.id)) setRequest(updated);
    });

  const onMarkParsed = () =>
    guarded(async () => {
      if (!request) return;
      const updated = await api.transition(request.id, "parsed");
      if (stillOpen(request.id)) setRequest(updated);
      await refreshList();
    });

  async function onSaveDesign(params: DesignParams) {
    if (!request) return;
    setDesignProblems([]);
    try {
      const d = await api.saveDesign(request.id, params);
      const updated = await api.getRequest(request.id);
      if (stillOpen(request.id)) {
        setDesign(d);
        setEstimate(null);
        setRequest(updated);
      }
      await refreshList();
    } catch (e) {
      if (e instanceof ApiError) setDesignProblems([e.message, ...e.problems]);
      else setError("Сервер недоступен");
    }
  }

  const onCalculate = () =>
    guarded(async () => {
      if (!request) return;
      const est = await api.calculateEstimate(request.id);
      const updated = await api.getRequest(request.id);
      if (stillOpen(request.id)) {
        setEstimate(est);
        setRequest(updated);
      }
      await refreshList();
    });

  const onSend = () =>
    guarded(async () => {
      if (!request) return;
      const updated = await api.transition(request.id, "sent");
      if (stillOpen(request.id)) setRequest(updated);
      await refreshList();
    });

  return (
    <div className="layout">
      <header className="topbar">
        <div className="brand">
          <span className="logo" aria-hidden="true">
            ▦
          </span>
          <div>
            <strong>OrderFlow</strong>
            <span className="muted"> · мастерская «Кедр»</span>
          </div>
        </div>
        <span className="demo-tag">демо · данные вымышленные</span>
      </header>
      <RequestList items={items} selectedId={selectedId} onSelect={select} />
      <main className="workspace">
        {request && <StatusSteps status={request.status} />}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <Intake
          key={request?.id ?? "new"}
          request={request}
          onCreate={onCreate}
          onSaveField={onSaveField}
          onMarkParsed={onMarkParsed}
        />
        {request && (
          <>
            <DesignPanel
              key={`${request.id}-${design?.request_id ?? "n"}-${request.status}`}
              request={request}
              design={design?.request_id === request.id ? design : null}
              materials={materials}
              problems={designProblems}
              onSave={onSaveDesign}
            />
            <EstimatePanel
              request={request}
              estimate={estimate?.request_id === request.id ? estimate : null}
              onCalculate={onCalculate}
              onSend={onSend}
            />
          </>
        )}
      </main>
    </div>
  );
}
