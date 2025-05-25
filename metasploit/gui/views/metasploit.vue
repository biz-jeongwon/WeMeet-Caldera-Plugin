<template>
  <div class="container">
    <h1>🧠 Metasploit AI Ability Generator</h1>
    <section class="card">
      <h2>⚙️ 모듈 검색 필터</h2>

      <label>플랫폼:</label>
      <select v-model="platform">
        <option disabled value="">-- 선택 --</option>
        <option>linux</option>
        <option>windows</option>
        <option>multi</option>
        <option>android</option>
      </select>

      <label>타입:</label>
      <select v-model="type">
        <option disabled value="">-- 선택 --</option>
        <option>exploit</option>
        <option>payload</option>
        <option>auxiliary</option>
        <option>post</option>
        <option>encoder</option>
        <option>evasion</option>
        <option>nop</option>
      </select>

      <label>CVE 연도 (선택):</label>
      <select v-model="cveYear">
        <option value="">-- 무시 --</option>
        <option v-for="year in cveYears" :key="year">{{ year }}</option>
      </select>

      <label>정렬 기준:</label>
      <select v-model="sortBy">
        <option value="">-- 무시 --</option>
        <option value="name">이름</option>
        <option value="date">공개일</option>
        <option value="rank">위험도</option>
        <option value="type">유형</option>
      </select>

      <label>정렬 순서:</label>
      <select v-model="sortOrder">
        <option value="">-- 무시 --</option>
        <option value="asc">오름차순</option>
        <option value="desc">내림차순</option>
      </select>

      <label>타겟 환경:</label>
      <input v-model="targetEnv" placeholder="예: Amazon Linux 2023" />

      <div class="search-bar">
        <button @click="searchModules" class="primary" :disabled="loading">🔍 모듈 검색</button>
        <span class="status-message">{{ searchMessage }}</span>
      </div>

      <label v-if="modules.length">모듈 필터링 (검색된 리스트 중):</label>
      <input v-if="modules.length" v-model="moduleSearch" placeholder="모듈 이름 키워드로 검색..." />

      <label v-if="filteredModules.length">검색된 모듈:</label>
      <select v-model="selectedModule" v-if="filteredModules.length">
        <option disabled value="">모듈 선택</option>
        <option v-for="m in filteredModules" :key="m">{{ m }}</option>
      </select>

      <button @click="generateCommand" class="primary" :disabled="!selectedModule">
        🧠 GPT로 명령어 생성
      </button>

      <div v-if="command">
        <h3>🌱 생성된 명령어 (수정 가능)</h3>
        <textarea v-model="command" rows="6" class="command-textarea" spellcheck="false" />
        <button @click="createAbility" class="primary" style="margin-top: 10px;">
          ⚙️ Ability 생성
        </button>
      </div>

      <p v-if="result" class="success">✅ {{ result }}</p>
      <p v-if="error" class="error">❌ {{ error }}</p>
    </section>
  </div>
</template>

<script>
export default {
  data() {
    return {
      platform: '',
      type: '',
      cveYear: '',
      sortBy: '',
      sortOrder: '',
      cveYears: ['2024', '2023', '2022', '2021', '2020'],
      modules: [],
      moduleSearch: '',
      selectedModule: '',
      moduleOptions: {},
      result: '',
      error: '',
      command: '',
      loading: false,
      searchMessage: '',
      targetEnv: ''
    }
  },
  computed: {
    filteredModules() {
      if (!this.moduleSearch) return this.modules
      const keyword = this.moduleSearch.toLowerCase()
      return this.modules.filter(m => m.toLowerCase().includes(keyword))
    }
  },
  methods: {
    async searchModules() {
      this.loading = true
      this.modules = []
      this.selectedModule = ''
      this.moduleOptions = {}
      this.result = ''
      this.error = ''
      this.command = ''
      this.searchMessage = '⏳ 검색 중입니다...'
      try {
        const res = await fetch('/plugins/metasploit/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            platform: this.platform,
            type: this.type,
            cveYear: this.cveYear,
            sortBy: this.sortBy,
            sortOrder: this.sortOrder
          })
        })
        const data = await res.json()
        if (res.ok) {
          this.modules = data.modules
          this.searchMessage = `✅ ${data.modules.length}개 모듈 검색됨`
        } else {
          this.error = data.error
          this.searchMessage = '❌ 검색 실패'
        }
      } catch (err) {
        this.error = err.message
        this.searchMessage = '❌ 검색 중 오류 발생'
      } finally {
        this.loading = false
      }
    },
    async generateCommand() {
      this.result = ''
      this.error = ''
      this.command = ''
      try {
        const res = await fetch('/plugins/metasploit/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            module: this.selectedModule,
            target_env: this.targetEnv
          })
        })
        const data = await res.json()
        if (res.ok) {
          this.command = data.command
        } else {
          this.error = data.error
        }
      } catch (err) {
        this.error = err.message
      }
    },
    async createAbility() {
      this.result = ''
      this.error = ''
      try {
        const res = await fetch('/plugins/metasploit/ability', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            module: this.selectedModule,
            command: this.command
          })
        })
        const data = await res.json()
        if (res.ok) {
          this.result = data.status + ': ' + data.path
        } else {
          this.error = data.error
        }
      } catch (err) {
        this.error = err.message
      }
    }
  }
}
</script>

<style scoped>
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
  font-size: 32px;
  margin-bottom: 30px;
  color: #cccccc;
}
.card {
  background: #1e1e1e;
  padding: 20px 25px;
  margin-bottom: 30px;
  border-radius: 12px;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
}
input, select, textarea {
  width: 100%;
  padding: 10px;
  margin-bottom: 15px;
  background-color: #2a2a2a;
  color: #f1f1f1;
  border: 1px solid #444;
  border-radius: 6px;
  font-size: 14px;
}
.command-textarea {
  font-family: monospace;
  background-color: #1a1a1a;
  color: #d4ffd4;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 10px;
}
.search-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}
.status-message {
  font-weight: bold;
  color: #ffaa44;
}
button.primary {
  background-color: #a066e0;
  color: white;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: bold;
}
button.primary:hover {
  background-color: #8a4dcc;
}
.success {
  margin-top: 10px;
  color: #66ff66;
}
.error {
  margin-top: 10px;
  color: #ff6666;
}
</style>
