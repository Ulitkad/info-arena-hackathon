<script setup>
import { inject } from 'vue';
import Icon from '../../components/Icon.vue';
const manager = inject('manager-page');
const { store, route, router, tab, catalog, members, requests, invites, rewards, modal, loading, search, message, groupName, subjectName, subjectColor, inviteGroup, assign, editingTeacher, inviteRole, renameTarget, renameName, reward, editRewardId, organizations, inviteUrl, organizationId, filteredMembers, pendingByGroup, studentCount, load, chooseOrganization, perform, routeTab, createGroup, createSubject, saveLinks, toggleLink, invite, moderate, copyInvite, approveAll, openTeacher, saveTeacherLoads, deleteMember, deleteTeacher, saveReward, editReward, deleteReward, openRename, saveRename } = manager;
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
          @click="
            editRewardId = null;
            reward = {
              name: '',
              kind: 'BADGE',
              threshold: 10,
              subject_id: '',
              asset_url: null,
              icon: 'award',
            };
            modal = 'reward';
          "
        >
          <Icon name="plus" :size="16" />Добавить уровень
        </button>
      </div>
      <div
        v-for="scope in [
          { subject_id: null, name: 'Общий боевой пропуск' },
          ...catalog.subjects.map((s) => ({ subject_id: s.id, name: s.name })),
        ]"
        :key="scope.subject_id || 'general'"
        class="reward-scope"
      >
        <div class="catalog-heading">
          <span class="eyebrow">{{ scope.name.toUpperCase() }}</span
          ><span class="subtle-count"
            >{{
              rewards.filter((r) => r.subject_id === scope.subject_id).length
            }}
            уровней</span
          >
        </div>
        <article
          v-for="item in rewards.filter(
            (r) => r.subject_id === scope.subject_id,
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
                { TITLE: "Звание", FRAME: "Рамка", BADGE: "Достижение" }[
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
          v-if="!rewards.some((r) => r.subject_id === scope.subject_id)"
          class="empty-inline"
        >
          Здесь будут появляться новые уровни.
        </p>
      </div>
    </section>

</template>
