# pyjevsim 성능 개선 제안

## 1. 스케줄러 우선순위 큐 도입 (고우선)
- **대상:** `pyjevsim/system_executor.py`의 `create_entity`, `schedule`, `handle_external_input_event`, `destroy_active_entity`
- **증상:** 매 이벤트마다 `deque`를 `sorted()`로 재정렬하여 O(N log N) 비용이 누적됨. 구조 실행기(`pyjevsim/structural_executor.py`) 역시 동일 패턴을 반복함.
- **개선안:**
  - `min_schedule_item`을 `heapq` 기반 우선순위 큐로 전환하고, `(req_time, obj_id, executor)` 튜플을 push/pop.
  - 구조 실행기 역시 동일 로직을 공유하도록 `ExecutorFactory` 레벨에서 공통 헬퍼 유틸리티 제공.
- **기대효과:** 메인 루프의 재정렬 비용 제거로 대규모 모델(수천 executor)에서 플레임그래프 기준 20~40% CPU 절감 예상.

## 2. 외부 이벤트 일괄 처리 (고우선)
- **대상:** `pyjevsim/system_executor.py`의 `handle_external_input_event`
- **증상:** 현재 한 번에 한 이벤트만 `heapq.heappop` 하고 즉시 리소팅, 동일 타임스탬프 이벤트가 많으면 반복 오버헤드 발생.
- **개선안:** 현재 글로벌 시간 이하 이벤트를 while 루프로 모두 pop → 메시지 전달, 처리 후에 단 한 번 큐 정렬/재계산.
- **기대효과:** 이벤트 폭주 구간에서 lock 경합 및 재정렬 계산 감소.

## 3. 메시지 복제를 최소화 (중우선)
- **대상:** `pyjevsim/system_executor.py:333` 인근 `output_handling`
- **증상:** 리스트일 때 `copy.deepcopy`를 호출해 불필요한 딥카피가 발생.
- **개선안:** 메시지 객체를 불변으로 두고 필요 시 새 `SysMessage` 인스턴스 생성 혹은 `list(msg)` 얕은 복사 사용. 구조 실행기의 `route_message`에서도 동일 패턴 존재.
- **기대효과:** 메시지량이 많은 모델에서 GC pressure 감소 및 throughput 향상.

## 4. 엔티티 스케줄링 자료구조 개선 (중우선)
- **대상:** `pyjevsim/system_executor.py:182` 인근 `create_entity`
- **증상:** 생성 대기 맵에서 매 호출마다 `min(self.waiting_obj_map)`로 최소 키 탐색. 엔티티 수가 많을 때 O(N log N) 비용.
- **개선안:**
  - `(inst_time, entity)` 힙 유지 혹은 `heapq`를 사용한 별도 생성 큐 도입.
  - 활성화 시점에만 pop 하여 `min_schedule_item`에 push.
- **기대효과:** 대규모 초기 로딩/동적 생성이 잦은 시뮬레이션에서 시작 시간 관리 비용 감소.

## 5. 메시지 전송 도구 재사용 (중우선)
- **대상:** `pyjevsim/system_executor.py:346`, `pyjevsim/structural_executor.py:79`
- **증상:** 루프마다 `MessageDeliverer()` 객체를 새로 생성. GC 및 메모리 할당 빈도가 높음.
- **개선안:**
  - 전용 풀(Pool)을 두거나, 함수 시작 시 로컬 인스턴스를 재사용하고 처리 후 `clear()` 호출.
- **기대효과:** 프레임당 객체 생성 수 감소, 특히 실시간 모드에서 GC 스톨 완화.

## 6. 스냅샷 I/O 최적화 (저우선)
- **대상:** `pyjevsim/snapshot_executor.py:187`, `pyjevsim/snapshot_manager.py:93`
- **증상:** 매 스냅샷마다 `os.makedirs`/`json.dump` 반복 호출, I/O 바운드 증가.
- **개선안:**
  - 디렉터리 존재 여부 캐시, 버퍼드 파일 쓰기 사용.
  - 잦은 스냅샷 시 비동기 쓰기(스레드/프로세스) 옵션 제공.
- **기대효과:** 빈번한 스냅샷 워크로드에서 I/O 지연 감소.

## 7. 모니터링 및 벤치마크 시나리오 구축
- **대상:** `tests` 및 `examples`
- **증상:** 현재 성능 회귀를 잡을 수 있는 벤치마크 부재.
- **개선안:**
  - 대규모 모델(수천 엔티티)과 메시지 폭주 시나리오를 생성하는 성능 테스트 스크립트 추가.
  - `pytest-benchmark` 또는 간단한 타이머 기반 계측으로 변경 효과 검증.
- **기대효과:** 개선안 도입 전후 성능 비교 가능, 회귀 테스트 자동화 기반 마련.

---

### 우선순위 요약
1. 스케줄러 우선순위 큐화 + 외부 이벤트 일괄 처리 → 메인 루프 병목 제거.
2. 메시지 핸들링 경량화(딥카피 제거, 오브젝트 재사용) → 메모리 및 GC 부담 감소.
3. 생성/스냅샷 부문 최적화 → 대규모 시뮬레이션 및 부가 기능 효율 개선.

### 제안 실행 순서
1. 힙 기반 스케줄러 리팩토링 및 단위 테스트 확장.
2. 메시지 경량화 및 구조 실행기/시스템 실행기 공통 헬퍼 추출.
3. 벤치마크 시나리오 작성 후 잔여 개선(생성 큐, 스냅샷) 적용.
