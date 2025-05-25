<template>
  <div class="container">
    <h1>🔧 Sliver Implant Manager</h1>

    <!-- 🔌 Sliver 서버 상태 확인 -->
    <section class="card">
      <h2>🔴 Sliver 서버 상태</h2>
      <hr>
      <p v-if="serverRunning">✅ 서버 실행 중</p>
      <p v-else-if="serverMessage">{{ serverMessage }}</p>
      <p v-else>❌ 서버 꺼져 있음</p>
      <button v-if="!serverRunning" @click="startServer" class="primary">서버 실행</button>
    </section>

    <!-- 💾 Implant 생성 -->
    <section class="card">
      <h2>💾 Implant 관리</h2>
      <hr>
      <br>
      <h2>Implant 생성</h2>
      <form @submit.prevent="generateImplant">
        <div class="form-group">
          <label>파일명:</label>
          <input type="text" v-model="implant.filename" placeholder="implant 파일 이름 입력">
        </div>
        <button type="submit" class="primary">Generate</button>
        <p class="result">{{ generateResult }}</p>
      </form>
      <br>
      <h2>Implant 리스트</h2>
      <button @click="loadImplants" class="secondary">새로고침</button>
      <ul class="session-list">
        <li v-for="file in implants" :key="file" class="session-item">
          📎 {{ file }}
          <div class="actions">
            <a :href="`/downloads/${file}`" class="download-link" download>다운로드</a>
            <button @click="deleteImplant(file)" class="small danger">삭제</button>
          </div>
        </li>
      </ul>
    </section>

    <!-- 📡 Job Listener -->
    <section class="card">
      <h2>📡 Job listener 관리</h2>
      <hr>
      <br>
      <h2>Job listener 생성</h2>
      <form @submit.prevent="startListener">
        <div class="form-group">
          <label>포트 번호:</label>
          <input type="number" v-model="listener.port" placeholder="예: 80" min="1" max="65535">
        </div>
        <button type="submit" class="primary">Listener 시작</button>
        <p class="result">{{ listenerResult }}</p>
      </form>
      <br>
      <h2>Job Listener 리스트</h2>
      <button @click="loadJobs" class="secondary">새로고침</button>
      <ul class="session-list">
        <li v-for="job in jobs" :key="job.id" class="session-item">
                📡 {{ job.id }} | {{ job.name }} | Port: {{ job.port }} | Protocol: {{ job.protocol }}
          <button @click="deleteListener(job.id)" class="small danger">삭제</button>
        </li>
      </ul>
    </section>

    <!-- 💻 Sliver 세션 리스트 -->
    <section class="card">
      <h2>💻 Sliver 세션 리스트</h2>
      <hr>
      <button @click="loadSessions" class="secondary">새로고침</button>
      <ul class="session-list">
        <li v-for="session in sessions" :key="session.id" class="session-item">
          💻 <strong>{{ session.id }}</strong>
          <span class="info">({{ session.arch }}, {{ session.remoteAddr }})</span>
          <div class="actions">
            <button @click="installAgent(session.id)" class="small">+ Agent 설치</button>
            <button @click="deleteSession(session.id)" class="small danger">삭제</button>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<script>
export default {
  name: 'SliverView',
  data() {
    return {
      implant: { filename: '' },
      generateResult: '',
      sessions: [],
      implants: [],
      jobs: [],
      listener: { port: 80 },
      listenerResult: '',
      serverRunning: false,
      serverMessage: ''
    };
  },
  methods: {
    async checkServerStatus() {
      try {
        const res = await fetch('/plugins/sliver/server-status');
        const result = await res.json();
        this.serverRunning = result.running;
      } catch (err) {
        console.error('서버 상태 확인 실패:', err);
      }
    },
    async startServer() {
      try {
        this.serverMessage = '🟡 서버 실행 중...';
        const res = await fetch('/plugins/sliver/start-server', { method: 'POST' });
        const result = await res.json();
        if (res.ok) {
          alert(result.status);
          this.serverRunning = true;
        } else {
          alert('서버 실행 실패: ' + result.error);
        }
      } catch (err) {
        alert('서버 실행 요청 실패: ' + err.message);
      } finally {
        this.serverMessage = '';
      }
    },
    async generateImplant() {
      try {
        if (!this.implant.filename) {
          this.generateResult = '❌ 파일명을 입력하세요.';
          return;
        }
        this.generateResult = '⏳ Implant 생성 중...';
        const res = await fetch('/plugins/sliver/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.implant)
        });
        const result = await res.json();
        if (res.ok) {
          this.generateResult = `✅ 생성 완료: ${result.filename}`;
          await this.loadImplants();
        } else {
          this.generateResult = `❌ 오류: ${result.error}`;
        }
      } catch (err) {
        this.generateResult = `❌ 요청 실패: ${err.message}`;
      }
    },
    async deleteImplant(filename) {
      if (!confirm(`정말 ${filename} 파일을 삭제하시겠습니까?`)) return;
      try {
        const res = await fetch('/plugins/sliver/delete-implant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename })
        });
        const result = await res.json();
        if (res.ok) {
          this.generateResult = `✅ ${filename} 삭제 완료`;
          await this.loadImplants();
        } else {
          this.generateResult = `❌ 삭제 오류: ${result.error}`;
        }
      } catch (err) {
        this.generateResult = `❌ 삭제 실패: ${err.message}`;
      }
    },
    async startListener() {
      try {
        const res = await fetch('/plugins/sliver/start-job', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.listener)
        });
        const result = await res.json();
        if (res.ok) {
          this.listenerResult = `✅ Listener 시작됨 (port ${this.listener.port})`;
          this.loadJobs();
        } else {
          this.listenerResult = `❌ 오류: ${result.error}`;
        }
      } catch (err) {
        this.listenerResult = `❌ 요청 실패: ${err.message}`;
      }
    },
    async deleteListener(id) {
      if (!confirm(`정말 Listener 포트 ${id}를 종료하시겠습니까?`)) return;
      try {
        const res = await fetch('/plugins/sliver/delete-listener', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        const result = await res.json();
        if (res.ok) {
          alert(result.status);
          this.loadJobs();
        } else {
          alert('❌ 오류: ' + result.error);
        }
      } catch (err) {
        alert('❌ 실패: ' + err.message);
      }
    },
    async deleteSession(sessionId) {
      if (!confirm(`정말 세션 ${sessionId}를 종료하시겠습니까?`)) return;
      try {
        const res = await fetch('/plugins/sliver/delete-session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId })
        });
        const result = await res.json();
        if (res.ok) {
          alert(result.status);
          this.loadSessions();
        } else {
          alert('❌ 오류: ' + result.error);
        }
      } catch (err) {
        alert('❌ 실패: ' + err.message);
      }
    },
    async installAgent(sessionId) {
      try {
        const calderaIP = location.hostname;
        const res = await fetch('/plugins/sliver/install-agent', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, caldera_ip: calderaIP })
        });
        const msg = await res.json();
        alert(msg.status || msg.error);
      } catch (err) {
        alert('요청 실패: ' + err.message);
      }
    },
    async loadImplants() {
      try {
        const res = await fetch('/plugins/sliver/implants');
        const list = await res.json();
        this.implants = Array.isArray(list) ? list : [];
      } catch (err) {
        console.error('Implant 리스트 로딩 실패:', err);
      }
    },
    async loadJobs() {
      try {
        const res = await fetch('/plugins/sliver/jobs');
        const list = await res.json();
        this.jobs = Array.isArray(list) ? list : [];
      } catch (err) {
        console.error('Jobs 로딩 실패:', err);
      }
    },
    async loadSessions() {
      try {
        const res = await fetch('/plugins/sliver/sessions');
        const data = await res.json();
        this.sessions = Array.isArray(data) ? data : [];
      } catch (err) {
        console.error('세션 로딩 실패:', err);
      }
    }
  },
  mounted() {
    this.checkServerStatus();
    this.loadImplants();
    this.loadJobs();
    this.loadSessions();
  }
};
</script>

<style scoped>
body {
  background-color: #161616;
}
.container {
  max-width: 720px;
  margin: 40px auto;
  font-family: 'Segoe UI', sans-serif;
  color: #eaeaea;
  padding: 0 20px;
  background-color: #161616;
}
h1 {
  font-weight: bold;
  font-size: 40px;
  margin-bottom: 30px;
  color: #cccccc
}
h2 {
  font-weight: bold;
  font-size: 24px;
  margin-bottom: 15px;
  color: #cccccc;
}
.card {
  background: #1e1e1e;
  padding: 20px 25px;
  margin-bottom: 30px;
  border-radius: 12px;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
}
.form-group {
  margin-bottom: 15px;
}
label {
  display: block;
  font-weight: 600;
  margin-bottom: 5px;
  color: #bbbbbb;
}
input[type="text"], input[type="number"] {
  width: 100%;
  padding: 8px 10px;
  background-color: #2a2a2a;
  color: #f1f1f1;
  border: 1px solid #444;
  border-radius: 6px;
  font-size: 14px;
}
button {
  cursor: pointer;
  font-size: 14px;
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
  transition: background 0.2s ease-in-out;
}
button.primary {
  background-color: #a066e0;
  color: white;
}
button.primary:hover {
  background-color: #8a4dcc;
}
button.secondary {
  background-color: #3498db;
  color: white;
  margin-bottom: 10px;
}
button.secondary:hover {
  background-color: #2980b9;
}
button.small {
  background-color: #2ecc71;
  color: white;
  font-size: 12px;
  margin-left: 10px;
}
button.small:hover {
  background-color: #27ae60;
}
button.danger {
  background-color: #e74c3c;
  margin-left: 10px;
}
button.danger:hover {
  background-color: #c0392b;
}
.result {
  margin-top: 10px;
  font-style: italic;
  color: #aaaaaa;
}
.download-link {
  color: #7ec0ee;
  margin-left: 10px;
  font-size: 13px;
  text-decoration: underline;
}
.session-list {
  list-style: none;
  padding-left: 0;
}
.session-item {
  padding: 10px;
  margin-bottom: 8px;
  background: #2a2a2a;
  border-radius: 8px;
  border: 1px solid #444;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.session-item .info {
  font-size: 13px;
  color: #999;
  margin-left: 10px;
}
.session-item .actions {
  display: flex;
  align-items: center;
}
</style>
