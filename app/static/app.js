async function postForm(url, formData) {
  const res = await fetch(url, { method: "POST", body: formData });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function setStatus(msg, kind) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.classList.remove("ok","err");
  if (kind) el.classList.add(kind);
}

async function loadHeaders(fileInputId, selectId) {
  const appU = document.getElementById("app_username").value;
  const appP = document.getElementById("app_password").value;
  const file = document.getElementById(fileInputId).files[0];
  if (!file) return;

  const fd = new FormData();
  fd.append("app_username", appU);
  fd.append("app_password", appP);
  fd.append("excel", file);

  setStatus("Reading headers…");
  const data = await postForm("/api/excel/headers", fd);

  const sel = document.getElementById(selectId);
  sel.innerHTML = `<option value="">Select column…</option>`;
  for (const h of data.headers) {
    const opt = document.createElement("option");
    opt.value = h;
    opt.textContent = h;
    sel.appendChild(opt);
  }
  setStatus("Headers loaded.");
}

document.getElementById("excel1").addEventListener("change", () => loadHeaders("excel1","col1"));
document.getElementById("excel2").addEventListener("change", () => loadHeaders("excel2","col2"));

document.getElementById("startBtn").addEventListener("click", async () => {
  try {
    const appU = document.getElementById("app_username").value;
    const appP = document.getElementById("app_password").value;

    const vessel = document.getElementById("vessel").value;
    const col1 = document.getElementById("col1").value;
    const col2 = document.getElementById("col2").value;

    const f1 = document.getElementById("excel1").files[0];
    const f2 = document.getElementById("excel2").files[0];

    if (!appU || !appP) throw new Error("Enter app username/password");
    if (!f1 || !f2) throw new Error("Upload both Excel files");
    if (!col1 || !col2) throw new Error("Select NED column for both files");
    if (!vessel) throw new Error("Select vessel");

    const fd = new FormData();
    fd.append("app_username", appU);
    fd.append("app_password", appP);
    fd.append("vessel", vessel);
    fd.append("col1", col1);
    fd.append("col2", col2);
    fd.append("excel1", f1);
    fd.append("excel2", f2);

    setStatus("Submitting job…");
    const created = await postForm("/api/jobs", fd);
    const jobId = created.job_id;

    setStatus(`Queued: ${jobId}`);
    document.getElementById("downloads").classList.add("hidden");

    const poll = async () => {
      const url = `/api/jobs/${jobId}?app_username=${encodeURIComponent(appU)}&app_password=${encodeURIComponent(appP)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Status failed");

      if (data.status === "QUEUED" || data.status === "RUNNING") {
        setStatus(`${data.status}…`);
        setTimeout(poll, 2000);
        return;
      }
      if (data.status === "FAILED") {
        setStatus(`FAILED: ${data.error || "Unknown error"}`, "err");
        return;
      }
      if (data.status === "COMPLETED") {
        setStatus("COMPLETED. Download outputs below.", "ok");
        const token = data.download_token;

        const d1 = document.getElementById("d1");
        const d2 = document.getElementById("d2");
        d1.href = `/download/${token}/excel1?app_username=${encodeURIComponent(appU)}&app_password=${encodeURIComponent(appP)}`;
        d2.href = `/download/${token}/excel2?app_username=${encodeURIComponent(appU)}&app_password=${encodeURIComponent(appP)}`;

        document.getElementById("downloads").classList.remove("hidden");
        return;
      }
      setStatus(`Unknown status: ${data.status}`);
    };

    setTimeout(poll, 1000);
  } catch (e) {
    setStatus(e.message, "err");
  }
});
