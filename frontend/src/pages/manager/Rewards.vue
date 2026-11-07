<script setup>
import { inject } from 'vue';
import Icon from '../../components/Icon.vue';
const manager = inject('manager-page');
  const { store, route, router, tab, catalog, members, requests, invites, rewards, modal, loading, search, message, groupName, subjectName, subjectColor, inviteGroup, assign, editingTeacher, inviteRole, renameTarget, renameName, reward, editRewardId, selectedRewardScope, organizations, inviteUrl, organizationId, filteredMembers, pendingByGroup, studentCount, load, chooseOrganization, perform, routeTab, createGroup, createSubject, saveLinks, toggleLink, invite, moderate, copyInvite, approveAll, openTeacher, saveTeacherLoads, deleteMember, deleteTeacher, saveReward, resetReward, editReward, deleteReward, openRename, saveRename } = manager;
</script>

<template>
<section class="management-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">РАЗВИТИЕ УЧАСТНИКОВ</span>
          <h2>Уровни и награды</h2>
        </div>
        <button
          class="btn primary"
           @click="resetReward"
        >
          <Icon name="plus" :size="16" />Добавить уровень
        </button>
      </div>
      <div class="battlepass-tabs" role="tablist" aria-label="Боевые пропуски">
        <button type="button" :class="{ active: selectedRewardScope === 'general' }" @click="selectedRewardScope = 'general'"><Icon name="layers" :size="15" /> Общий пропуск</button>
        <button v-for="subject in catalog.subjects" :key="subject.id" type="button" :class="{ active: selectedRewardScope === subject.id }" @click="selectedRewardScope = subject.id"><span class="pass-color" :style="{ background: subject.color }"></span>{{ subject.name }}</button>
      </div>
      <div class="reward-scope">
        <div class="catalog-heading">
          <span class="eyebrow">{{ (selectedRewardScope === 'general' ? 'Общий боевой пропуск' : catalog.subjects.find(s => s.id === selectedRewardScope)?.name || '').toUpperCase() }}</span
          ><span class="subtle-count"
            >{{
              rewards.filter((r) => r.subject_id === (selectedRewardScope === 'general' ? null : selectedRewardScope)).length
            }}
            уровней</span
          >
        </div>
        <article
          v-for="item in rewards.filter(
            (r) => r.subject_id === (selectedRewardScope === 'general' ? null : selectedRewardScope),
          )"
          :key="item.id"
          class="manager-reward-row panel"
        >
          <span
            class="reward-art"
            :class="`reward-art-${item.kind.toLowerCase()}`"
            ><img
              v-if="item.asset_url"
              :src="item.asset_url"
              :alt="item.name" /><Icon
              v-else
              :name="item.icon || 'award'"
              :size="20" /></span
          ><span class="manager-reward-name"
            ><strong>{{ item.name }}</strong
            ><small
              >{{
                  { TITLE: "Звание", FRAME: "Рамка", BADGE: "Достижение", CUSTOM: "Кастомная награда" }[
                  item.kind
                ]
              }}
              ·
              {{
                item.threshold ? `${item.threshold} баллов` : "Особая награда"
              }}</small
            ></span
          ><span v-if="item.special" class="chip neutral">Системная</span
          ><span v-else class="button-row"
            ><button
              class="icon-btn"
              :aria-label="`Изменить награду ${item.name}`"
              @click="editReward(item)"
            >
              <Icon name="pencil" :size="16" /></button
            ><button
              class="icon-btn danger-icon"
              :aria-label="`Удалить награду ${item.name}`"
              @click="deleteReward(item)"
            >
              <Icon name="trash" :size="16" /></button
          ></span>
        </article>
        <p
          v-if="!rewards.some((r) => r.subject_id === (selectedRewardScope === 'general' ? null : selectedRewardScope))"
          class="empty-inline"
        >
          Здесь будут появляться новые уровни.
        </p>
      </div>
    </section>

</template>
