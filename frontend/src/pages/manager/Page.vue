<script setup>
import { provide } from 'vue';
import { useManagerPage } from '../../composables/useManagerPage';
import Icon from '../../components/Icon.vue';
import ManagerRequests from './Requests.vue';
import ManagerGroups from './Groups.vue';
import ManagerTeachers from './Teachers.vue';
import ManagerRewards from './Rewards.vue';
import ManagerModals from './Modals.vue';
const manager = useManagerPage();
provide('manager-page', manager);
const { store, route, router, tab, catalog, members, requests, invites, rewards, modal, loading, search, message, groupName, subjectName, subjectColor, inviteGroup, assign, editingTeacher, inviteRole, renameTarget, renameName, reward, editRewardId, selectedRewardScope, organizations, inviteUrl, organizationId, filteredMembers, pendingByGroup, studentCount, load, chooseOrganization, perform, routeTab, createGroup, createSubject, saveLinks, toggleLink, invite, moderate, copyInvite, approveAll, openTeacher, saveTeacherLoads, deleteMember, deleteTeacher, saveReward, resetReward, editReward, deleteReward, openRename, saveRename } = manager;
</script>

<template>
  <section class="manager-page">
    <label v-if="store.user.role === 'ADMIN'" class="field-label organization-picker">Учреждение
      <select :value="organizationId" @change="chooseOrganization"><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select>
    </label>
    <div v-if="message" class="inline-alert">
      <Icon name="x-circle" :size="16" />{{ message }}
    </div>
    <div class="manager-stats">
      <div class="stat-card panel">
        <span class="stat-icon subjects"><Icon name="users" /></span
        ><span
          ><strong>{{ studentCount }}</strong
          ><small>учеников</small></span
        >
      </div>
      <div class="stat-card panel">
        <span class="stat-icon wins"><Icon name="book" /></span
        ><span
          ><strong>{{ catalog.groups.length }}</strong
          ><small>учебных групп</small></span
        >
      </div>
      <div class="stat-card panel">
        <span class="stat-icon awards"><Icon name="bell" /></span
        ><span
          ><strong>{{ requests.length }}</strong
          ><small>новых заявок</small></span
        >
      </div>
      <div class="stat-card panel">
        <span class="stat-icon events-stat"><Icon name="award" /></span
        ><span
          ><strong>{{ rewards.filter((r) => !r.special).length }}</strong
          ><small>наград</small></span
        >
      </div>
    </div>
    <div class="manager-tabs" role="tablist">
      <button
        v-for="item in [
          { id: 'requests', title: 'Заявки', icon: 'bell' },
          { id: 'groups', title: 'Группы и предметы', icon: 'book' },
          { id: 'teachers', title: 'Преподаватели', icon: 'graduation' },
          { id: 'rewards', title: 'Награды', icon: 'award' },
        ]"
        :key="item.id"
        role="tab"
        :aria-selected="tab === item.id"
        :class="{ active: tab === item.id }"
        @click="routeTab(item.id)"
      >
        <Icon :name="item.icon" :size="16" />{{ item.title
        }}<span
          v-if="item.id === 'requests' && requests.length"
          class="tab-count"
          >{{ requests.length }}</span
        >
      </button>
    </div>
    <ManagerRequests v-if="tab === 'requests'" />
    <ManagerGroups v-else-if="tab === 'groups'" />
    <ManagerTeachers v-else-if="tab === 'teachers'" />
    <ManagerRewards v-else-if="tab === 'rewards'" />
    <ManagerModals />
  </section>
</template>
