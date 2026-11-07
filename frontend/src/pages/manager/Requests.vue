<script setup>
import { inject } from 'vue';
import Icon from '../../components/Icon.vue';
import Avatar from '../../components/Avatar.vue';
const manager = inject('manager-page');
const { store, route, router, tab, catalog, members, requests, invites, rewards, modal, loading, search, message, groupName, subjectName, subjectColor, inviteGroup, assign, editingTeacher, inviteRole, renameTarget, renameName, reward, editRewardId, organizations, inviteUrl, organizationId, filteredMembers, pendingByGroup, studentCount, load, chooseOrganization, perform, routeTab, createGroup, createSubject, saveLinks, toggleLink, invite, moderate, copyInvite, approveAll, openTeacher, saveTeacherLoads, deleteMember, deleteTeacher, saveReward, editReward, deleteReward, openRename, saveRename } = manager;
</script>

<template>
<section class="management-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">НОВЫЕ УЧАСТНИКИ</span>
          <h2>Заявки на вступление</h2>
        </div>
        <button
          v-if="requests.length"
          class="btn secondary small"
          @click="load()"
        >
          <Icon name="activity" :size="15" />Обновить
        </button>
      </div>
      <div v-if="!requests.length" class="empty-page panel">
        <span class="empty-icon"><Icon name="users" :size="28" /></span>
        <h3>Все спокойно, все заявки рассмотрены</h3>
        <p>
          Новые участники появятся здесь, когда перейдут по ссылке-приглашению.
        </p>
      </div>
      <section
        v-for="row in pendingByGroup"
        :key="row.group.id"
        class="request-group panel"
      >
        <div class="request-group-head">
          <span class="group-icon"><Icon name="users" :size="18" /></span
          ><span
            ><strong>{{ row.group.name }}</strong
            ><small
              >{{ row.items.length }}
              {{
                row.items.length === 1 ? "новая заявка" : "новые заявки"
              }}</small
            ></span
          ><button
            v-if="row.items.length > 1"
            class="btn secondary small"
            @click="approveAll(row.group)"
          >
            <Icon name="check-check" :size="15" />Принять всех
          </button>
        </div>
        <article v-for="item in row.items" :key="item.id" class="request-row">
          <Avatar :user="item.student" :size="43" />
          <div class="request-user">
            <strong>{{ item.student.display_name }}</strong
            ><span>@{{ item.student.username || "без username" }}</span
            ><small>В группе {{ row.group.name }}</small>
          </div>
          <button
            class="icon-btn approve-btn"
            :aria-label="`Принять ${item.student.display_name}`"
            @click="moderate(item, true)"
          >
            <Icon name="check" :size="18" /></button
          ><button
            class="icon-btn danger-icon"
            :aria-label="`Отклонить ${item.student.display_name}`"
            @click="moderate(item, false)"
          >
            <Icon name="x" :size="18" />
          </button>
        </article>
      </section>
      <button class="btn primary invite-student-action" @click="modal = 'invite-student'">
        <Icon name="link" :size="16" />Приглашение для ученика
      </button>
    </section>

</template>
