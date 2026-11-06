import { loadSample } from "./api-client.js";

const won = (amount) => `${amount.toLocaleString("ko-KR")}원`;
const time = (value) => new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul", dateStyle: "short", timeStyle: "short",
}).format(new Date(value));

try {
  const [runs, seats, reservation] = await Promise.all([
    loadSample("runs"), loadSample("seats"), loadSample("reservation-paid"),
  ]);
  for (const run of runs.items) {
    const row = document.createElement("tr");
    for (const value of [run.service_number, run.train_type_name,
      time(run.departure_at), time(run.arrival_at), won(run.fares[0].amount)]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    }
    document.querySelector("#runs").append(row);
  }
  const selected = new Map();
  for (const seat of seats) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-outline-primary";
    button.disabled = !seat.available;
    button.setAttribute("aria-pressed", "false");
    button.textContent = `${seat.carriage_no}호차 ${seat.seat_number} · ${won(seat.amount)}`;
    button.addEventListener("click", () => {
      if (selected.has(seat.seat_id)) selected.delete(seat.seat_id);
      else selected.set(seat.seat_id, seat.seat_number);
      button.classList.toggle("active", selected.has(seat.seat_id));
      button.setAttribute("aria-pressed", String(selected.has(seat.seat_id)));
      document.querySelector("#selection").textContent = selected.size
        ? `선택한 좌석: ${[...selected.values()].join(", ")}` : "선택한 좌석이 없습니다.";
    });
    document.querySelector("#seats").append(button);
  }
  document.querySelector("#reservation").textContent = JSON.stringify(reservation, null, 2);
} catch (error) {
  document.querySelector("#preview-error").textContent = error.message;
}
