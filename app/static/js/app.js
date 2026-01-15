let poller = null;

document.getElementById("f").onsubmit = async (e) => {
  e.preventDefault();

  const btn = e.target.querySelector("button");
  btn.disabled = true;
  btn.textContent = "Running...";

  const fd = new FormData(e.target);

  const res = await fetch("/automation/start", {
    method: "POST",
    body: fd
  });

  const data = await res.json();
  document.getElementById("out").textContent = JSON.stringify(data, null, 2);

  poller = setInterval(async () => {
    const r = await fetch(`/automation/status/${data.run_id}`);
    const s = await r.json();
    document.getElementById("out").textContent = JSON.stringify(s, null, 2);

    if (s.status === "SUCCESS" || s.status === "FAILED") {
      clearInterval(poller);
      btn.disabled = false;
      btn.textContent = "Start";
    }
  }, 2000);
};
