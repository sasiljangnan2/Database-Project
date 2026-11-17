import { APIError, api } from "./api-client.js";

/* -------------------------------------------------
 * 1. 기본 설정 / 상태
 * ------------------------------------------------- */

const $ = (selector) => document.querySelector(selector);

const STATIONS = ["서울", "수원", "대전", "동대구", "부산"];
const DISTANCES = [0, 35, 160, 290, 417];

const TRAIN_DATA = [
  { id: "KTX101", name: "KTX 101", departure: "08:00", fullFare: 59800, minutes: 165 },
  { id: "KTX103", name: "KTX 103", departure: "09:00", fullFare: 59800, minutes: 160 },
  { id: "ITX203", name: "ITX 203", departure: "10:20", fullFare: 37400, minutes: 240 },
  { id: "KTX107", name: "KTX 107", departure: "13:00", fullFare: 59800, minutes: 170 },
  { id: "KTX111", name: "KTX 111", departure: "17:10", fullFare: 59800, minutes: 165 }
];

const STATUS_LABELS = {
  pending: "결제 대기",
  issued: "발권 완료",
  partial: "일부 환불",
  expired: "예약 만료",
  cancelled: "취소",
  refunded: "환불 완료"
};

const DEMO_HOLD_MS = 10 * 60 * 1000;
const KOREA_TIME_ZONE = "Asia/Seoul";
const koreanCalendar = new Intl.DateTimeFormat("en-CA", {
  timeZone: KOREA_TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit"
});

function localDate(date = new Date()) {
  const { year, month, day } = Object.fromEntries(
    koreanCalendar.formatToParts(date).map(({ type, value }) => [type, value])
  );
  return `${year}-${month}-${day}`;
}

function tomorrow() {
  return localDate(new Date(Date.now() + 24 * 60 * 60 * 1000));
}

const state = {
  view: "home",
  user: null,
  search: {
    from: "서울",
    to: "부산",
    date: tomorrow(),
    passengers: 1
  },
  results: [],
  train: null,
  seatClass: "standard",
  car: 1,
  selectedSeats: [],
  bookings: [],
  currentBookingId: null,
  bookingFilter: "all"
};

const app = $("#app");

/* -------------------------------------------------
 * 2. 공통 유틸리티
 * ------------------------------------------------- */

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[char]));
}

function money(value) {
  return `${Number(value).toLocaleString("ko-KR")}원`;
}

function dateText(value) {
  return new Date(`${value}T00:00:00+09:00`).toLocaleDateString("ko-KR", {
    timeZone: KOREA_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short"
  });
}

function timeText(minutes) {
  return `${Math.floor(minutes / 60)}시간 ${minutes % 60}분`;
}

function addMinutes(time, minutes) {
  const [hour, minute] = time.split(":").map(Number);
  const total = hour * 60 + minute + minutes;

  return [
    String(Math.floor(total / 60) % 24).padStart(2, "0"),
    String(total % 60).padStart(2, "0")
  ].join(":");
}

function classText(value) {
  return value === "standard" ? "일반실" : "특실";
}

function seatText(seat) {
  return `${seat.car}호차 ${seat.row}${seat.letter}`;
}

function seatKey(seat) {
  return `${seat.car}-${seat.row}-${seat.letter}`;
}

function unitPrice(train = state.train, seatClass = state.seatClass) {
  return seatClass === "premium"
    ? Math.round(train.fare * 1.4 / 100) * 100
    : train.fare;
}

function timestamp(time = Date.now()) {
  return new Date(time).toLocaleString("ko-KR", { timeZone: KOREA_TIME_ZONE });
}

let toastTimer;

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");

  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    element.classList.remove("show");
  }, 3200);
}

function currentBooking() {
  return state.bookings.find((booking) => booking.id === state.currentBookingId);
}

function departureAt(query, train) {
  return Date.parse(`${query.date}T${train.departure}:00+09:00`);
}

function refreshExpiredBookings() {
  const now = Date.now();
  for (const booking of state.bookings) {
    if (booking.status === "pending" && now >= booking.expiresAt) {
      booking.status = "expired";
    }
  }
}

function activeTickets(booking) {
  return booking.seats.filter((seat) => !seat.cancelled);
}

function canRefundTickets(booking) {
  return booking && ["issued", "partial"].includes(booking.status)
    && Date.now() < departureAt(booking.query, booking.train);
}

function showAuth(target = "login", email = "") {
  navigate("auth");
  if (email) $("#login-email").value = email;
  $(`#${target}-email`).focus();
}

function statusBadge(status) {
  return `
    <span class="status ${status}">
      ${STATUS_LABELS[status]}
    </span>
  `;
}

function details(rows) {
  return `
    <dl class="detail-list">
      ${rows.map(([label, value]) => `
        <div>
          <dt>${escapeHTML(label)}</dt>
          <dd>${escapeHTML(value)}</dd>
        </div>
      `).join("")}
    </dl>
  `;
}

function steps(active) {
  const names = ["열차 조회", "좌석 선택", "예약 확인", "결제", "발권 완료"];

  return `
    <div class="steps" aria-label="예약 진행 단계">
      ${names.map((name, index) => `
        <span
          class="step ${index === active ? "active" : index < active ? "done" : ""}"
          ${index === active ? 'aria-current="step"' : ""}
        >
          ${index + 1}. ${name}
        </span>
      `).join("")}
    </div>
  `;
}

function heading(title, subtitle = "") {
  return `
    <div class="page-heading">
      <div>
        <h1>${escapeHTML(title)}</h1>
        ${subtitle ? `<p>${escapeHTML(subtitle)}</p>` : ""}
      </div>
    </div>
  `;
}

/* -------------------------------------------------
 * 3. 데모 운행 / 좌석 데이터
 *
 * 실제 프로젝트에서는 아래 데이터 조회 부분을
 * 백엔드 API 호출로 교체합니다.
 * ------------------------------------------------- */

function searchTrains(query) {
  const fromIndex = STATIONS.indexOf(query.from);
  const toIndex = STATIONS.indexOf(query.to);

  if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) {
    return [];
  }

  const distance = Math.abs(
    DISTANCES[toIndex] - DISTANCES[fromIndex]
  );

  const ratio = distance / 417;
  const direction = fromIndex < toIndex ? "down" : "up";

  const offsetRatio = direction === "down"
    ? DISTANCES[fromIndex] / 417
    : (417 - DISTANCES[fromIndex]) / 417;

  return TRAIN_DATA.map((train) => {
    const duration = Math.max(20, Math.round(train.minutes * ratio));
    const departure = addMinutes(
      train.departure,
      Math.round(train.minutes * offsetRatio)
    );

    return {
      ...train,
      serviceId: `${train.id}-${direction}`,
      departure,
      arrival: addMinutes(departure, duration),
      duration,
      fare: Math.max(5000, Math.round(train.fullFare * ratio / 100) * 100)
    };
  }).filter((train) => departureAt(query, train) > Date.now());
}

function carsFor(seatClass) {
  return seatClass === "standard" ? [1, 2, 3] : [4];
}

function seatsForCar(car) {
  const result = [];

  for (let row = 1; row <= 6; row += 1) {
    for (const letter of ["A", "B", "C", "D"]) {
      result.push({ car, row, letter });
    }
  }

  return result;
}

function intervalsOverlap(aFrom, aTo, bFrom, bTo) {
  const a = [STATIONS.indexOf(aFrom), STATIONS.indexOf(aTo)].sort((x, y) => x - y);
  const b = [STATIONS.indexOf(bFrom), STATIONS.indexOf(bTo)].sort((x, y) => x - y);

  return Math.max(a[0], b[0]) < Math.min(a[1], b[1]);
}

function isOccupied(train, seatClass, seat, query = state.search) {
  // 항상 같은 결과가 나오는 데모용 기존 예약 좌석
  const seed = `${train.serviceId}-${query.date}`
    .split("")
    .reduce((sum, char) => sum + char.charCodeAt(0), 0);

  const index = seat.car * 30 + seat.row * 4 + "ABCD".indexOf(seat.letter);
  const mockOccupied = (seed + index) % 9 === 0;

  if (mockOccupied) return true;

  // 이 페이지에서 만든 체험 예약만 좌석 현황에 반영한다.
  return state.bookings.some((booking) => {
    if (!["pending", "issued", "partial"].includes(booking.status)) {
      return false;
    }
    if (booking.status === "pending" && Date.now() >= booking.expiresAt) return false;

    return (
      booking.train.serviceId === train.serviceId &&
      booking.query.date === query.date &&
      booking.seatClass === seatClass &&
      intervalsOverlap(
        booking.query.from,
        booking.query.to,
        query.from,
        query.to
      ) &&
      activeTickets(booking).some((savedSeat) => seatKey(savedSeat) === seatKey(seat))
    );
  });
}

function remainingSeats(train, seatClass) {
  return carsFor(seatClass)
    .flatMap(seatsForCar)
    .filter((seat) => !isOccupied(train, seatClass, seat))
    .length;
}

/* -------------------------------------------------
 * 4. 공통 내비게이션
 * ------------------------------------------------- */

function renderHeader() {
  $("#auth-nav").innerHTML = state.user
    ? `
      <button type="button" data-action="profile">
        ${escapeHTML(state.user.name)}님
      </button>
      <button type="button" data-action="logout">로그아웃</button>
    `
    : `
      <button type="button" data-action="login">로그인</button>
      <button type="button" data-action="signup">회원가입</button>
    `;
}

function navigate(view) {
  state.view = view;
  render();
  app.focus();
  window.scrollTo({ top: 0, behavior: "auto" });
}

function render() {
  refreshExpiredBookings();
  renderHeader();

  const views = {
    home: homeView,
    auth: authView,
    results: resultsView,
    seats: seatsView,
    confirm: confirmView,
    payment: paymentView,
    complete: completeView,
    refund: refundView,
    bookings: bookingsView,
    profile: profileView,
    help: helpView
  };

  app.innerHTML = (views[state.view] || homeView)();
}

/* -------------------------------------------------
 * 5. 메인 검색
 * ------------------------------------------------- */

function stationOptions(selected) {
  return STATIONS.map((station) => `
    <option value="${station}" ${station === selected ? "selected" : ""}>
      ${station}역
    </option>
  `).join("");
}

function homeView() {
  return `
    <section class="hero has-photo">
      <div class="hero-copy">
        <h1>
          HRAIL과 함께하는<br>
          더 빠르고 편리한 여행
        </h1>
        <p>출발역과 도착역을 골라 열차 예매를 체험해 보세요.</p>
      </div>
    </section>

    <section class="panel search-box" aria-label="열차 검색">
      <form id="search-form" class="search-grid">
        <div class="field">
          <label for="from">출발역</label>
          <select id="from" name="from">
            ${stationOptions(state.search.from)}
          </select>
        </div>

        <button
          class="swap-button"
          type="button"
          data-action="swap"
          aria-label="출발역과 도착역 바꾸기"
        >⇄</button>

        <div class="field">
          <label for="to">도착역</label>
          <select id="to" name="to">
            ${stationOptions(state.search.to)}
          </select>
        </div>

        <div class="field date-field">
          <label for="date">출발일</label>
          <input
            id="date"
            name="date"
            type="date"
            min="${localDate()}"
            value="${state.search.date}"
            required
          >
        </div>

        <div class="field passenger-field">
          <label for="passengers">인원</label>
          <select id="passengers" name="passengers">
            ${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((count) => `
              <option
                value="${count}"
                ${count === state.search.passengers ? "selected" : ""}
              >
                성인 ${count}명
              </option>
            `).join("")}
          </select>
        </div>

        <button class="btn-primary" type="submit">
          검색하기
        </button>
      </form>
    </section>

    <section class="feature-grid" aria-label="서비스 안내">
      <article class="panel feature-card">
        <div class="feature-icon">↗</div>
        <h2>열차 검색</h2>
        <p>출발역과 도착역, 날짜에 맞는 예시 운행과 운임을 확인하세요.</p>
      </article>

      <article class="panel feature-card">
        <div class="feature-icon">▦</div>
        <h2>좌석 선택</h2>
        <p>호차와 좌석을 확인하고 함께 여행할 자리를 직접 선택하세요.</p>
      </article>

      <article class="panel feature-card">
        <div class="feature-icon">✓</div>
        <h2>체험 내역</h2>
        <p>모의 결제, 승차권 확인, 좌석별 환불을 체험하세요.</p>
      </article>
    </section>
  `;
}

/* -------------------------------------------------
 * 6. 로그인 / 회원가입
 * ------------------------------------------------- */

function authView() {
  return `
    ${heading("HRAIL 회원 서비스")}

    <section class="panel auth-layout">
      <div class="auth-panel">
        <h2>로그인</h2>
        <form id="login-form" class="form-stack mt-4" method="post">
          <div class="field">
            <label for="login-email">이메일</label>
            <input
              id="login-email"
              name="email"
              type="email"
              maxlength="254"
              placeholder="example@email.com"
              autocomplete="username"
              required
            >
          </div>

          <div class="field">
            <label for="login-password">비밀번호</label>
            <input
              id="login-password"
              name="password"
              type="password"
              placeholder="비밀번호를 입력하세요"
              maxlength="128"
              autocomplete="current-password"
              required
            >
          </div>

          <p class="form-feedback" data-form-feedback role="status" hidden></p>
          <button class="btn-primary full-width" type="submit">
            로그인
          </button>
        </form>
      </div>

      <div class="auth-panel">
        <h2>회원가입</h2>
        <form id="signup-form" class="form-stack mt-4" method="post">
          <div class="field">
            <label for="signup-email">이메일</label>
            <input
              id="signup-email"
              name="email"
              type="email"
              maxlength="254"
              autocomplete="email"
              placeholder=" example@email.com"
              required
            >
          </div>

          <div class="field">
            <label for="signup-password">비밀번호 입력</label>
            <input
              id="signup-password"
              name="password"
              type="password"
              minlength="10"
              maxlength="128"
              placeholder="10자 이상 입력"
              autocomplete="new-password"
              required
            >
          </div>

          <div class="field">
            <label for="signup-confirm">비밀번호 확인</label>
            <input
              id="signup-confirm"
              name="confirm"
              type="password"
              minlength="10"
              maxlength="128"
              autocomplete="new-password"
              required
            >
          </div>

          <div class="field">
            <label for="signup-name">이름</label>
            <input
              id="signup-name"
              name="name"
              maxlength="100"
              autocomplete="name"
              placeholder="홍길동"
              required
            >
          </div>

          <div class="field">
            <label for="signup-phone">연락처</label>
            <input
              id="signup-phone"
              name="phone"
              type="tel"
              placeholder="010-1234-5678"
              autocomplete="tel"
              maxlength="30"
              required
            >
          </div>

          <p class="form-feedback" data-form-feedback role="status" hidden></p>
          <button class="btn-primary full-width" type="submit">
            회원가입
          </button>
        </form>
      </div>
    </section>
  `;
}

/* -------------------------------------------------
 * 7. 검색 결과
 * ------------------------------------------------- */

function routeSummary() {
  return `
    <div class="route-summary">
      <div>
        <strong>
          ${state.search.from}역 → ${state.search.to}역
        </strong>
        <span class="muted route-meta">· ${dateText(state.search.date)}</span>
        <span class="muted route-meta">· 성인 ${state.search.passengers}명</span>
      </div>

      <button
        type="button"
        class="btn-secondary btn-small"
        data-action="home"
      >
        다시 검색하기
      </button>
    </div>
  `;
}

function resultsView() {
  return `
    ${steps(0)}
    ${heading("열차 검색 결과", "직통 운행 열차와 좌석 현황을 확인하세요.")}
    ${routeSummary()}

    <section class="panel">
      <div class="table-wrap">
        <table class="train-table" role="table">
          <caption class="visually-hidden">
            검색된 열차의 시간, 잔여석 및 성인 1인 일반실 운임
          </caption>

          <thead>
            <tr>
              <th scope="col">열차번호</th>
              <th scope="col">출발역</th>
              <th scope="col">출발시간</th>
              <th scope="col">도착역</th>
              <th scope="col">도착시간</th>
              <th scope="col">소요시간</th>
              <th scope="col">일반실</th>
              <th scope="col">특실</th>
              <th scope="col">운임</th>
              <th scope="col">선택</th>
            </tr>
          </thead>

          <tbody>
            ${state.results.map((train) => {
              const standard = remainingSeats(train, "standard");
              const premium = remainingSeats(train, "premium");
              const soldOut = Math.max(standard, premium) < state.search.passengers;

              return `
                <tr>
                  <td class="train-name">${train.name}</td>
                  <td data-label="출발역">${state.search.from}역</td>
                  <td class="time" data-label="출발시간">${train.departure}</td>
                  <td data-label="도착역">${state.search.to}역</td>
                  <td class="time" data-label="도착시간">${train.arrival}</td>
                  <td data-label="소요시간">${timeText(train.duration)}</td>
                  <td data-label="일반실">${standard}석</td>
                  <td data-label="특실">${premium}석</td>
                  <td class="price" data-label="일반실 운임">${money(train.fare)}</td>
                  <td>
                    <button
                      type="button"
                      class="btn-primary btn-small"
                      data-action="select-train"
                      data-id="${train.serviceId}"
                      ${soldOut ? "disabled" : ""}
                    >
                      ${soldOut ? "좌석 부족" : "좌석 선택"}
                    </button>
                  </td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      </div>

      ${state.results.length === 0 ? `
        <div class="empty-state">
          조건에 맞는 운행이 없습니다. 날짜를 변경해보세요.
        </div>
      ` : ""}

      <p class="muted mt-3 mb-0" style="font-size:12px">
        운임은 성인 1인 일반실 기준입니다.
      </p>
    </section>
  `;
}

/* -------------------------------------------------
 * 8. 좌석 선택
 * ------------------------------------------------- */

function seatButton(seat) {
  const occupied = isOccupied(state.train, state.seatClass, seat);
  const selected = state.selectedSeats.some(
    (item) => seatKey(item) === seatKey(seat)
  );

  return `
    <button
      type="button"
      class="seat ${selected ? "selected" : ""}"
      data-action="toggle-seat"
      data-seat="${seatKey(seat)}"
      aria-label="${seatText(seat)} ${occupied ? "선택 불가" : ""}"
      aria-pressed="${selected}"
      ${occupied ? "disabled" : ""}
    >
      ${occupied ? "×" : `${seat.row}${seat.letter}`}
    </button>
  `;
}

function seatsView() {
  const total = unitPrice() * state.selectedSeats.length;

  return `
    ${steps(1)}
    ${heading("좌석 선택", "함께 여행할 좌석을 직접 선택하세요.")}
    ${routeSummary()}

    <div class="two-column">
      <section class="panel">
        <h2>${state.train.name}</h2>

        <p class="muted">
          ${state.train.departure} 출발 · ${state.train.arrival} 도착
        </p>

        <div class="segmented" aria-label="좌석 등급">
          ${["standard", "premium"].map((seatClass) => `
            <button
              type="button"
              class="${state.seatClass === seatClass ? "active" : ""}"
              data-action="seat-class"
              data-value="${seatClass}"
              aria-pressed="${state.seatClass === seatClass}"
            >
              ${classText(seatClass)}
              · ${money(unitPrice(state.train, seatClass))}
            </button>
          `).join("")}
        </div>

        <div class="car-tabs" aria-label="호차 선택">
          ${carsFor(state.seatClass).map((car) => `
            <button
              type="button"
              class="${state.car === car ? "active" : ""}"
              data-action="car"
              data-value="${car}"
              aria-pressed="${state.car === car}"
            >
              ${car}호차
            </button>
          `).join("")}
        </div>

        <div class="seat-direction">↑ 열차 진행 방향</div>

        <div class="seat-grid">
          <span></span>
          <span class="seat-header">A · 창가</span>
          <span class="seat-header">B</span>
          <span></span>
          <span class="seat-header">C</span>
          <span class="seat-header">D · 창가</span>

          ${Array.from({ length: 6 }, (_, index) => {
            const row = index + 1;

            return `
              <span class="row-number">${row}</span>
              ${seatButton({ car: state.car, row, letter: "A" })}
              ${seatButton({ car: state.car, row, letter: "B" })}
              <span aria-hidden="true"></span>
              ${seatButton({ car: state.car, row, letter: "C" })}
              ${seatButton({ car: state.car, row, letter: "D" })}
            `;
          }).join("")}
        </div>

        <div class="seat-legend">
          <span><i class="legend-dot"></i>선택 가능</span>
          <span><i class="legend-dot selected"></i>선택 좌석</span>
          <span><i class="legend-dot unavailable"></i>선택 불가</span>
        </div>
      </section>

      <aside class="panel">
        <h2>선택한 좌석</h2>

        <p class="muted">
          ${state.selectedSeats.length} / ${state.search.passengers}석 선택
        </p>

        <div class="selection-list">
          ${state.selectedSeats.length ? state.selectedSeats.map((seat) => `
            <div class="selected-seat">
              <span>
                ${seatText(seat)} · ${classText(state.seatClass)}
              </span>
              <button
                type="button"
                class="remove-seat"
                data-action="remove-seat"
                data-seat="${seatKey(seat)}"
                aria-label="${seatText(seat)} 선택 해제"
              >×</button>
            </div>
          `).join("") : `
            <div class="empty-state">좌석을 선택해주세요.</div>
          `}
        </div>

        <div class="total-row">
          <span>총 결제 금액</span>
          <strong>${money(total)}</strong>
        </div>

        <button
          type="button"
          class="btn-primary full-width"
          data-action="confirm"
          ${state.selectedSeats.length !== state.search.passengers ? "disabled" : ""}
        >
          다음 단계
        </button>

        <button
          type="button"
          class="btn-secondary full-width mt-2"
          data-action="results"
        >
          검색 결과로
        </button>
      </aside>
    </div>
  `;
}

/* -------------------------------------------------
 * 9. 예약 확인
 * ------------------------------------------------- */

function confirmView() {
  const total = unitPrice() * state.selectedSeats.length;

  return `
    ${steps(2)}
    ${heading("체험 예약 확인")}

    <section class="panel">
      <div class="two-column">
        <div>
          <h2>열차 정보</h2>
          ${details([
            ["열차번호", state.train.name],
            ["출발역", `${state.search.from}역`],
            ["도착역", `${state.search.to}역`],
            ["출발일", dateText(state.search.date)],
            ["출발시간", state.train.departure],
            ["도착시간", state.train.arrival]
          ])}
        </div>

        <div>
          <h2>승객 및 좌석 정보</h2>
          ${details([
            ["승객 수", `${state.search.passengers}명`],
            ["좌석번호", state.selectedSeats.map(seatText).join(", ")],
            ["좌석등급", classText(state.seatClass)],
            ["총 결제 금액", money(total)]
          ])}

          <div class="notice mt-4">
            체험 좌석은 최대 10분간 확보됩니다. 열차 출발 시각이 더 이르면 출발 시각까지 결제할 수 있습니다.
          </div>
        </div>
      </div>

      <div class="button-row">
        <button
          type="button"
          class="btn-secondary"
          data-action="seats"
        >
          좌석 다시 선택
        </button>

        <button
          type="button"
          class="btn-primary"
          data-action="reserve"
        >
          체험 예약하기
        </button>
      </div>
    </section>
  `;
}

/* -------------------------------------------------
 * 10. 결제
 * ------------------------------------------------- */

function paymentView() {
  const booking = currentBooking();

  if (!booking || booking.status !== "pending") {
    return `
      ${heading("모의 결제")}
      <section class="panel">
        <p>${booking?.status === "expired" ? "결제 기한이 지났습니다." : "결제할 체험 예약이 없습니다."}</p>
        <button type="button" class="btn-secondary" data-action="bookings">체험 내역으로</button>
      </section>
    `;
  }

  return `
    ${steps(3)}
    ${heading("모의 결제", "결제 수단을 선택하면 체험 승차권이 발권됩니다.")}

    <form id="payment-form">
      <div class="two-column">
        <section class="panel">
          <h2>결제 수단을 선택해주세요.</h2>

          <div class="form-stack mt-4">
            ${[
              ["card", "신용카드"],
              ["simple", "간편결제"],
              ["transfer", "계좌이체"]
            ].map(([value, label], index) => `
              <label class="payment-option">
                <input
                  type="radio"
                  name="method"
                  value="${value}"
                  ${index === 0 ? "checked" : ""}
                >
                <span>${label}</span>
              </label>
            `).join("")}
          </div>
        </section>

        <aside class="panel">
          <h2>결제 금액</h2>

          <div class="payment-amount">
            ${money(booking.total)}
          </div>

          ${details([
            ["열차", booking.train.name],
            ["구간", `${booking.query.from} → ${booking.query.to}`],
            ["인원", `${booking.seats.length}명`],
            ["좌석등급", classText(booking.seatClass)],
            ["결제 기한", timestamp(booking.expiresAt)]
          ])}

          <button class="btn-primary full-width mt-4" type="submit">
            ${money(booking.total)} 모의 결제
          </button>
        </aside>
      </div>

      <div class="button-row">
        <button
          type="button"
          class="btn-secondary"
          data-action="bookings"
        >
          나중에 결제하기
        </button>

        <button
          type="button"
          class="btn-danger-soft"
          data-action="cancel-booking"
          data-id="${booking.id}"
        >
          예약 취소
        </button>
      </div>
    </form>
  `;
}

/* -------------------------------------------------
 * 11. 승차권
 * ------------------------------------------------- */

function completeView() {
  const booking = currentBooking();

  if (!booking || !["issued", "partial", "refunded"].includes(booking.status)) {
    return `${heading("체험 승차권")}<div class="panel">발급된 체험 승차권이 없습니다.</div>`;
  }

  return `
    ${steps(4)}

    <div class="two-column">
      <section class="success-section">
        <div class="success-icon">✓</div>
        <h1>체험 승차권</h1>
        <p class="muted">선택한 좌석별 승차권과 환불 상태를 확인하세요.</p>

        <div class="button-row" style="justify-content:center">
          <button
            class="btn-primary"
            type="button"
            data-action="bookings"
          >
            체험 내역
          </button>

          <button
            class="btn-secondary"
            type="button"
            data-action="print"
          >
            승차권 인쇄
          </button>
        </div>
      </section>

      <article class="panel ticket">
        <div class="ticket-header">HRAIL · 체험 승차권</div>

        <div class="ticket-body">
          <div class="d-flex justify-content-between align-items-center">
            <strong class="train-name">${booking.train.name}</strong>
            ${statusBadge(booking.status)}
          </div>

          <div class="ticket-route">
            ${booking.query.from}역 → ${booking.query.to}역
          </div>

          ${details([
            ["출발일", dateText(booking.query.date)],
            ["운행시간", `${booking.train.departure} → ${booking.train.arrival}`],
            ["좌석등급", classText(booking.seatClass)],
            ["인원", `${booking.seats.length}명`],
            ["결제금액", money(booking.total)]
          ])}

          <ul class="pass-list">
            ${booking.seats.map((seat) => `
              <li>
                <strong>${seatText(seat)}</strong>
                <span>${seat.ticketNumber}</span>
                <span class="${seat.cancelled ? "ticket-status-cancelled" : ""}">
                  ${seat.cancelled ? "환불 완료" : "발권 완료"}
                </span>
              </li>
            `).join("")}
          </ul>
        </div>

        <div class="ticket-bottom">
          예약번호 ${booking.id}
        </div>
      </article>
    </div>
  `;
}

/* -------------------------------------------------
 * 12. 마이페이지 / 예약 내역
 * ------------------------------------------------- */

function sidebar(active) {
  return `
    <aside class="panel sidebar">
      <h2>이용 메뉴</h2>

      <button
        type="button"
        class="${active === "bookings" ? "active" : ""}"
        data-action="bookings"
      >
        체험 내역
      </button>

      <button
        type="button"
        class="${active === "profile" ? "active" : ""}"
        data-action="profile"
      >
        회원정보 수정
      </button>

      <button type="button" data-action="help">취소 및 환불 안내</button>
      ${state.user ? '<button type="button" data-action="logout">로그아웃</button>' : ""}
    </aside>
  `;
}

function filterMatches(booking, filter) {
  if (filter === "all") return true;
  if (filter === "cancelled") {
    return ["cancelled", "partial", "refunded"].includes(booking.status);
  }
  return booking.status === filter;
}

function bookingCard(booking) {
  const paid = ["issued", "partial", "refunded"].includes(booking.status);
  const canRefund = canRefundTickets(booking);

  return `
    <article class="booking-card">
      <div>
        ${statusBadge(booking.status)}
        <small class="ms-2">예약번호 ${booking.id}</small>

        <h3>
          ${booking.train.name}
          · ${booking.query.from} → ${booking.query.to}
        </h3>

        <p>
          ${dateText(booking.query.date)}
          · ${booking.train.departure} → ${booking.train.arrival}
        </p>

        <p>
          ${classText(booking.seatClass)}
          · ${booking.seats.map((seat) => `${seatText(seat)}${seat.cancelled ? " (환불)" : ""}`).join(", ")}
        </p>

        <strong class="price d-inline-block mt-2">
          ${money(booking.total)}
        </strong>

        ${booking.status === "pending" ? `<p>결제 기한 ${timestamp(booking.expiresAt)}</p>` : ""}
        <details class="transaction-log">
          <summary>모의 결제·환불 기록 (${booking.transactions.length})</summary>

          ${booking.transactions.length ? `
            <ul>
              ${booking.transactions.map((transaction) => `
                <li>
                  ${escapeHTML(transaction.time)}
                  · ${escapeHTML(transaction.label)}
                  · ${money(transaction.amount)}
                </li>
              `).join("")}
            </ul>
          ` : `<p>결제 기록이 없습니다.</p>`}
        </details>
      </div>

      <div class="booking-actions">
        ${booking.status === "pending" ? `
          <button
            class="btn-primary btn-small"
            type="button"
            data-action="open-payment"
            data-id="${booking.id}"
          >
            모의 결제
          </button>
        ` : ""}

        ${paid ? `
          <button
            class="btn-primary btn-small"
            type="button"
            data-action="open-ticket"
            data-id="${booking.id}"
          >
            승차권 보기
          </button>
        ` : ""}

        ${booking.status === "pending" ? `
          <button
            class="btn-secondary btn-small"
            type="button"
            data-action="cancel-booking"
            data-id="${booking.id}"
          >
            예약 취소
          </button>
        ` : ""}

        ${canRefund ? `
          <button
            class="btn-secondary btn-small"
            type="button"
            data-action="refund-tickets"
            data-id="${booking.id}"
          >
            승차권 선택 환불
          </button>
        ` : ""}

        ${booking.status === "pending" || canRefund ? `
          <button
            class="btn-secondary btn-small"
            type="button"
            data-action="change-booking"
            data-id="${booking.id}"
          >
            일정 변경
          </button>
        ` : ""}
      </div>
    </article>
  `;
}

function bookingsView() {
  const bookings = state.bookings.slice().reverse();

  const filters = [
    ["all", "전체"],
    ["pending", "결제 대기"],
    ["issued", "발권 완료"],
    ["cancelled", "취소·환불"],
    ["expired", "예약 만료"]
  ];

  const filtered = bookings.filter(
    (booking) => filterMatches(booking, state.bookingFilter)
  );

  return `
    ${heading("체험 내역", "이 페이지에서 만든 예매 체험 기록입니다. 새로고침하면 기록이 초기화됩니다.")}

    <div class="mypage-layout">
      ${sidebar("bookings")}

      <section class="panel">
        <div class="filter-tabs" aria-label="예약 상태 필터">
          ${filters.map(([value, label]) => `
            <button
              type="button"
              class="${state.bookingFilter === value ? "active" : ""}"
              data-action="booking-filter"
              data-value="${value}"
              aria-pressed="${state.bookingFilter === value}"
            >
              ${label}
              (${bookings.filter((booking) => filterMatches(booking, value)).length})
            </button>
          `).join("")}
        </div>

        ${filtered.length ? filtered.map(bookingCard).join("") : `
          <div class="empty-state">
            <h3>해당하는 체험 예약이 없습니다.</h3>
            <button
              type="button"
              class="btn-primary"
              data-action="home"
            >
              예매 체험하기
            </button>
          </div>
        `}
      </section>
    </div>
  `;
}

function refundView() {
  const booking = currentBooking();
  if (!canRefundTickets(booking)) {
    return `
      ${heading("승차권 선택 환불")}
      <section class="panel">
        <p>환불할 수 있는 체험 승차권이 없습니다.</p>
        <button type="button" class="btn-secondary" data-action="bookings">체험 내역으로</button>
      </section>
    `;
  }
  return `
    ${heading("승차권 선택 환불")}
    <section class="panel">
      <form id="ticket-refund-form" class="form-stack">
        <fieldset class="form-stack">
          <legend>환불할 좌석</legend>
          ${activeTickets(booking).map((seat) => `
            <label class="refund-choice">
              <input type="checkbox" name="seat" value="${seatKey(seat)}">
              <span>${seatText(seat)}</span>
              <strong>${money(booking.farePerSeat)}</strong>
            </label>
          `).join("")}
        </fieldset>
        <div class="button-row">
          <button type="button" class="btn-secondary" data-action="bookings">돌아가기</button>
          <button type="submit" class="btn-primary">선택 승차권 모의 환불</button>
        </div>
      </form>
    </section>
  `;
}

function profileView() {
  return `
    ${heading("회원정보 수정")}

    <div class="mypage-layout">
      ${sidebar("profile")}

      <section class="panel">
        <form id="profile-form" class="form-stack" method="post">
          <div class="field">
            <label for="profile-email">이메일</label>
            <input
              id="profile-email"
              type="email"
              value="${escapeHTML(state.user.email)}"
              readonly
            >
          </div>

          <div class="field">
            <label for="profile-name">이름</label>
            <input
              id="profile-name"
              name="name"
              value="${escapeHTML(state.user.name)}"
              maxlength="100"
              required
            >
          </div>

          <div class="field">
            <label for="profile-phone">연락처</label>
            <input
              id="profile-phone"
              name="phone"
              type="tel"
              value="${escapeHTML(state.user.phone)}"
              placeholder="010-1234-5678"
              maxlength="30"
              required
            >
          </div>

          <p class="form-feedback" data-form-feedback role="status" hidden></p>
          <div class="button-row">
            <button class="btn-primary" type="submit">변경사항 저장</button>
          </div>
        </form>

        <hr class="my-4">
        <form id="password-form" class="form-stack" method="post">
          <h2>비밀번호 변경</h2>
          <input type="hidden" name="username" autocomplete="username" value="${escapeHTML(state.user.email)}">
          <div class="field">
            <label for="current-password">현재 비밀번호</label>
            <input id="current-password" name="current_password" type="password"
              autocomplete="current-password" maxlength="128" required>
          </div>
          <div class="field">
            <label for="new-password">새 비밀번호</label>
            <input id="new-password" name="new_password" type="password"
              autocomplete="new-password" minlength="10" maxlength="128" required>
          </div>
          <div class="field">
            <label for="confirm-password">새 비밀번호 확인</label>
            <input id="confirm-password" name="confirm" type="password"
              autocomplete="new-password" minlength="10" maxlength="128" required>
          </div>
          <p class="form-feedback" data-form-feedback role="status" hidden></p>
          <div class="button-row">
            <button class="btn-primary" type="submit">비밀번호 변경</button>
          </div>
        </form>
      </section>
    </div>
  `;
}

/* -------------------------------------------------
 * 13. 고객센터
 * ------------------------------------------------- */

function helpView() {
  return `
    ${heading("이용 안내")}

    <section class="panel form-stack">
      <details open>
        <summary>
          <strong>예매 체험은 어떻게 하나요?</strong>
        </summary>

        <p class="muted mt-3">
          출발역·도착역·출발일·인원을 선택하고 열차를 검색해주세요.
          원하는 열차와 좌석을 선택한 뒤 예약 정보를 확인하고
          모의 결제를 완료하면 체험 승차권을 확인할 수 있습니다.
        </p>
      </details>

      <hr>

      <details>
        <summary>
          <strong>승차권은 어디에서 확인하나요?</strong>
        </summary>

        <p class="muted mt-3">
          체험 내역에서 모의 결제가 완료된 예약의 승차권 보기 버튼을 선택해 주세요.
        </p>
      </details>

      <hr>

      <details>
        <summary>
          <strong>일정을 변경하고 싶어요.</strong>
        </summary>

        <p class="muted mt-3">
          일정 변경은 기존 예약을 취소한 후 다시 예약하는 방식으로
          진행됩니다. 체험 내역에서 일정 변경을 선택하고,
          취소 확인 후 새로운 일정을 검색해주세요.
        </p>
      </details>

      <hr>

      <details>
        <summary>
          <strong>예약 취소는 어떻게 하나요?</strong>
        </summary>

        <p class="muted mt-3">
          결제 대기 예약은 체험 내역에서 취소할 수 있습니다.
          모의 결제 후에는 출발 전에 환불할 좌석을 선택해 주세요.
        </p>
      </details>
    </section>
  `;
}

/* -------------------------------------------------
 * 14. 예약 처리
 * ------------------------------------------------- */

function createReservation() {
  if (state.selectedSeats.length !== state.search.passengers) {
    toast("승객 수에 맞게 좌석을 선택해주세요.");
    return;
  }

  const departure = departureAt(state.search, state.train);
  const now = Date.now();

  if (departure <= now) {
    toast("출발 시간이 지난 열차입니다. 다시 검색해주세요.");
    navigate("home");
    return;
  }

  const unavailable = state.selectedSeats.some(
    (seat) => isOccupied(state.train, state.seatClass, seat)
  );

  if (unavailable) {
    state.selectedSeats = [];
    navigate("seats");
    toast("선택한 좌석 상태가 변경되었습니다. 다시 선택해주세요.");
    return;
  }

  const id = `HR-${now.toString(36).toUpperCase()}-${state.bookings.length + 1}`;
  const farePerSeat = unitPrice();

  const booking = {
    id,
    query: { ...state.search },
    train: { ...state.train },
    seatClass: state.seatClass,
    seats: state.selectedSeats.map((seat, index) => ({
      ...seat, ticketNumber: `${id}-${index + 1}`, cancelled: false
    })),
    farePerSeat,
    total: farePerSeat * state.selectedSeats.length,
    status: "pending",
    transactions: [],
    expiresAt: Math.min(now + DEMO_HOLD_MS, departure)
  };

  state.bookings.push(booking);
  state.currentBookingId = booking.id;
  state.selectedSeats = [];

  navigate("payment");
  toast("체험 예약이 생성되었습니다.");
}

function refundTickets(booking, selectedKeys) {
  if (!canRefundTickets(booking)) {
    toast("출발 전에 발권된 체험 승차권만 환불할 수 있습니다.");
    return false;
  }

  const selected = activeTickets(booking).filter((seat) => selectedKeys.includes(seatKey(seat)));
  if (!selected.length) {
    toast("환불할 좌석을 선택해 주세요.");
    return false;
  }
  for (const seat of selected) seat.cancelled = true;
  booking.status = activeTickets(booking).length ? "partial" : "refunded";
  booking.transactions.push({
    label: `모의 환불 · ${selected.map(seatText).join(", ")}`,
    amount: booking.farePerSeat * selected.length,
    time: timestamp()
  });
  return true;
}

function cancelBooking(id, changeSchedule = false) {
  refreshExpiredBookings();
  const booking = state.bookings.find((item) => item.id === id);
  if (!booking || (booking.status !== "pending" && !(changeSchedule && canRefundTickets(booking)))) {
    navigate("bookings");
    toast("취소할 수 없는 체험 예약입니다.");
    return;
  }

  const message = changeSchedule
    ? "기존 체험 예약을 취소하고 새 일정을 선택할까요?"
    : "체험 예약을 취소할까요?";
  if (!window.confirm(message)) return;

  if (booking.status === "pending") {
    refreshExpiredBookings();
    if (booking.status === "expired") {
      navigate("bookings");
      toast("체험 예약이 만료되었습니다.");
      return;
    }
    booking.status = "cancelled";
  } else if (!refundTickets(booking, activeTickets(booking).map(seatKey))) {
    navigate("bookings");
    return;
  }

  if (changeSchedule) {
    state.search = {
      ...booking.query,
      date: booking.query.date < localDate() ? tomorrow() : booking.query.date
    };

    state.train = null;
    state.selectedSeats = [];
    navigate("home");
    toast("체험 예약을 취소했습니다. 새 일정을 검색해 주세요.");
  } else {
    state.bookingFilter = "all";
    navigate("bookings");
    toast("체험 예약을 취소했습니다.");
  }
}

function setFormFeedback(form, message, isError = false) {
  const feedback = form.querySelector("[data-form-feedback]");
  feedback.textContent = message;
  feedback.classList.toggle("is-error", isError);
  feedback.hidden = !message;
}

let memberRequestPending = false;
async function memberRequest(control, action) {
  if (memberRequestPending) return;
  memberRequestPending = true;
  const form = control.form;
  control.disabled = true;
  if (form) {
    setFormFeedback(form, "처리 중입니다…");
    form.setAttribute("aria-busy", "true");
  }

  try {
    await action();
  } catch (error) {
    const apiError = error instanceof APIError;
    const message = apiError && error.status < 500
      ? error.message
      : "회원 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.";
    if (apiError && error.status === 401 && state.user) {
      const email = state.user.email;
      api.clearAccessToken();
      state.user = null;
      showAuth("login", email);
      setFormFeedback($("#login-form"), `${message} 다시 로그인해 주세요.`, true);
    } else if (form?.isConnected) {
      setFormFeedback(form, message, true);
    } else {
      toast(message);
    }
  } finally {
    memberRequestPending = false;
    control.disabled = false;
    form?.removeAttribute("aria-busy");
  }
}

async function submitMemberForm(form, data, control) {
  const isRegistration = form.id === "signup-form";
  const isPasswordChange = form.id === "password-form";
  if (isRegistration && data.password !== data.confirm) {
    setFormFeedback(form, "비밀번호가 일치하지 않습니다.", true);
    form.elements.confirm.focus();
    return;
  }
  if (isPasswordChange && data.new_password !== data.confirm) {
    setFormFeedback(form, "새 비밀번호가 일치하지 않습니다.", true);
    form.elements.confirm.focus();
    return;
  }
  if ((isRegistration || form.id === "profile-form") && (!data.name.trim() || !data.phone.trim())) {
    setFormFeedback(form, "이름과 연락처를 입력해 주세요.", true);
    (data.name.trim() ? form.elements.phone : form.elements.name).focus();
    return;
  }

  await memberRequest(control, async () => {
    switch (form.id) {
      case "login-form": {
        const { access_token: token } = await api.request("/auth/login", {
          method: "POST", body: { email: data.email.trim(), password: data.password }
        });
        if (!token) throw new Error("Missing access token");
        api.setAccessToken(token);
        try {
          const user = await api.request("/users/me");
          if (!user?.id) throw new Error("Missing member");
          state.user = user;
        } catch (error) {
          api.clearAccessToken();
          throw error;
        }
        if (state.view === "auth") navigate("profile");
        else renderHeader();
        toast("로그인되었습니다.");
        break;
      }
      case "signup-form": {
        const user = await api.request("/auth/register", {
          method: "POST", body: {
            email: data.email.trim(), password: data.password,
            name: data.name.trim(), phone: data.phone.trim()
          }
        });
        if (!user?.id) throw new Error("Missing registered member");
        if (form.isConnected) {
          form.reset();
          $("#login-email").value = user.email;
          $("#login-password").focus();
          setFormFeedback($("#login-form"), "회원가입이 완료되었습니다. 로그인해 주세요.");
          setFormFeedback(form, "");
        } else {
          toast("회원가입이 완료되었습니다. 로그인해 주세요.");
        }
        break;
      }
      case "profile-form": {
        const user = await api.request("/users/me", {
          method: "PATCH", body: { name: data.name.trim(), phone: data.phone.trim() }
        });
        if (!user?.id) throw new Error("Missing updated member");
        state.user = user;
        renderHeader();
        if (form.isConnected) {
          form.elements.name.value = user.name;
          form.elements.phone.value = user.phone;
          setFormFeedback(form, "회원정보를 저장했습니다.");
        } else {
          toast("회원정보를 저장했습니다.");
        }
        break;
      }
      case "password-form": {
        const email = state.user.email;
        await api.request("/users/me/password", {
          method: "POST", body: {
            current_password: data.current_password, new_password: data.new_password
          }
        });
        api.clearAccessToken();
        state.user = null;
        showAuth("login", email);
        setFormFeedback($("#login-form"), "비밀번호를 변경했습니다. 새 비밀번호로 로그인해 주세요.");
        break;
      }
    }
  });
}

/* -------------------------------------------------
 * 15. 버튼 이벤트
 * ------------------------------------------------- */

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button || button.disabled) return;

  const action = button.dataset.action;
  const id = button.dataset.id;
  const value = button.dataset.value;

  switch (action) {
    case "home":
      navigate("home");
      break;

    case "help":
      navigate("help");
      break;

    case "login":
    case "signup":
      showAuth(action);
      break;

    case "logout":
      if (!state.user) break;
      void memberRequest(button, async () => {
        await api.request("/auth/logout", { method: "POST" });
        api.clearAccessToken();
        state.user = null;
        if (state.view === "profile") navigate("home");
        else render();
        toast("로그아웃되었습니다.");
      });
      break;

    case "bookings":
      navigate("bookings");
      break;

    case "profile":
      if (state.user) navigate("profile");
      else showAuth();
      break;

    case "swap": {
      const from = $("#from");
      const to = $("#to");
      [from.value, to.value] = [to.value, from.value];
      break;
    }

    case "select-train":
      state.train = state.results.find((train) => train.serviceId === id);
      if (!state.train || departureAt(state.search, state.train) <= Date.now()) {
        state.results = searchTrains(state.search);
        navigate("results");
        toast("출발 시간이 지난 열차입니다.");
        break;
      }
      state.seatClass = remainingSeats(state.train, "standard") >= state.search.passengers
        ? "standard"
        : "premium";
      state.car = carsFor(state.seatClass)[0];
      state.selectedSeats = [];

      navigate("seats");
      break;

    case "results":
      navigate("results");
      break;

    case "seats":
      navigate("seats");
      break;

    case "seat-class":
      if (state.seatClass === value) return;
      state.seatClass = value;
      state.car = carsFor(value)[0];
      state.selectedSeats = [];
      render();
      toast("좌석 등급이 변경되어 선택한 좌석이 초기화되었습니다.");
      break;

    case "car":
      state.car = Number(value);
      render();
      break;

    case "toggle-seat": {
      const [car, row, letter] = button.dataset.seat.split("-");
      const seat = { car: Number(car), row: Number(row), letter };
      const key = seatKey(seat);

      const selected = state.selectedSeats.some(
        (item) => seatKey(item) === key
      );

      if (selected) {
        state.selectedSeats = state.selectedSeats.filter(
          (item) => seatKey(item) !== key
        );
      } else {
        if (isOccupied(state.train, state.seatClass, seat)) {
          toast("선택할 수 없는 좌석입니다.");
          return;
        }

        if (state.selectedSeats.length >= state.search.passengers) {
          toast(`최대 ${state.search.passengers}석까지 선택할 수 있습니다.`);
          return;
        }

        state.selectedSeats.push(seat);
      }

      render();

      // 좌석을 선택해도 키보드 포커스를 유지
      app.querySelector(
        `[data-action="toggle-seat"][data-seat="${key}"]`
      )?.focus();

      break;
    }

    case "remove-seat":
      state.selectedSeats = state.selectedSeats.filter(
        (seat) => seatKey(seat) !== button.dataset.seat
      );
      render();
      break;

    case "confirm":
      if (state.selectedSeats.length !== state.search.passengers) {
        toast("승객 수에 맞게 좌석을 선택해주세요.");
        return;
      }
      navigate("confirm");
      break;

    case "reserve":
      createReservation();
      break;

    case "open-payment":
      state.currentBookingId = id;
      navigate("payment");
      break;

    case "open-ticket":
      state.currentBookingId = id;
      navigate("complete");
      break;

    case "refund-tickets":
      state.currentBookingId = id;
      navigate("refund");
      break;

    case "cancel-booking":
      cancelBooking(id);
      break;

    case "change-booking":
      cancelBooking(id, true);
      break;

    case "booking-filter":
      state.bookingFilter = value;
      render();
      break;

    case "print":
      window.print();
      break;
  }
});

/* -------------------------------------------------
 * 16. 폼 제출 이벤트
 * ------------------------------------------------- */

document.addEventListener("submit", (event) => {
  const form = event.target;

  if (![
    "search-form",
    "login-form",
    "signup-form",
    "profile-form",
    "password-form",
    "payment-form",
    "ticket-refund-form"
  ].includes(form.id)) {
    return;
  }

  event.preventDefault();

  if (!form.reportValidity()) return;

  const fields = new FormData(form);
  const data = Object.fromEntries(fields);

  switch (form.id) {
    case "search-form": {
      if (data.from === data.to) {
        toast("출발역과 도착역은 다르게 선택해주세요.");
        $("#to").focus();
        return;
      }

      if (!data.date || data.date < localDate()) {
        toast("오늘 이후의 출발일을 선택해주세요.");
        return;
      }

      state.search = {
        from: data.from,
        to: data.to,
        date: data.date,
        passengers: Number(data.passengers)
      };

      state.results = searchTrains(state.search);
      state.train = null;
      state.selectedSeats = [];
      navigate("results");
      break;
    }

    case "login-form":
    case "signup-form":
    case "profile-form":
    case "password-form":
      void submitMemberForm(form, data, event.submitter ?? form.querySelector('button[type="submit"]'));
      break;

    case "payment-form": {
      refreshExpiredBookings();
      const booking = currentBooking();

      if (booking?.status === "expired") {
        state.bookingFilter = "all";
        navigate("bookings");
        toast("결제 기한이 지나 체험 예약이 만료되었습니다.");
        return;
      }
      if (!booking || booking.status !== "pending") return;

      const methodNames = {
        card: "신용카드",
        simple: "간편결제",
        transfer: "계좌이체"
      };

      if (!methodNames[data.method]) {
        toast("결제 수단을 선택해주세요.");
        return;
      }

      booking.status = "issued";
      booking.transactions.push({
        label: `${methodNames[data.method]} 모의 결제 완료`,
        amount: booking.total,
        time: timestamp()
      });

      navigate("complete");
      toast("모의 결제가 완료되어 체험 승차권이 발권되었습니다.");
      break;
    }

    case "ticket-refund-form": {
      if (!refundTickets(currentBooking(), fields.getAll("seat"))) return;
      state.bookingFilter = "all";
      navigate("bookings");
      toast("선택한 체험 승차권을 환불했습니다.");
      break;
    }
  }
});

render();
