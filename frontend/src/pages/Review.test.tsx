import '@testing-library/jest-dom/vitest';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {Review} from './Review';
import {reviewApi} from '../api/reviews';
import {requestApi} from '../api/requests';
import type {StreamEvent} from '../state/events';
let emitReviewEvent:(event:StreamEvent)=>void=()=>undefined;
vi.mock('../state/events',()=>({useEventStream:(_f:unknown,_s:unknown,onEvent:(event:StreamEvent)=>void)=>{emitReviewEvent=onEvent;return{status:'connected',lastSeq:0}}}));
const row=(over:Record<string,unknown>={})=>({id:'rvw_1',request_id:'req_1',run_id:'run_1',revision_id:'rev_1',draft_version:1,review_version:1,status:'pending',reasons:['정보 부족'],...over});
const detail=(over:Record<string,unknown>={})=>({review:row(over),request:{title:'요청',request_text:'원문 내용'},judgment:{ai_need:'정보 부족'},outputs:[],drafts:[],history:[],final_classifications:{ai_need:'정보 부족'},final_draft_version:1});
vi.mock('../api/reviews',()=>({reviewApi:{list:vi.fn(),detail:vi.fn(),decide:vi.fn()}}));
vi.mock('../api/requests',()=>({requestApi:{detail:vi.fn().mockResolvedValue({revisions:[{id:'rev_1',text:'원문 내용'}]}),judgment:vi.fn(),evidence:vi.fn(),document:vi.fn()}}));
const renderAt=(url='/review')=>render(<MemoryRouter initialEntries={[url]}><Review/></MemoryRouter>);
beforeEach(()=>{cleanup();vi.clearAllMocks();vi.mocked(reviewApi.list).mockImplementation(async(status='pending')=>({reviews:status==='pending'?[row() as any]:[]}));vi.mocked(reviewApi.detail).mockResolvedValue(detail() as any);vi.mocked(requestApi.detail).mockResolvedValue({revisions:[{id:'rev_1',text:'원문 내용'}]} as any)});
describe('review list title and source permission',()=>{
 it('refreshes the queue after a review is created elsewhere',async()=>{
  vi.mocked(reviewApi.list).mockResolvedValue({reviews:[]} as any);renderAt();await waitFor(()=>expect(reviewApi.list).toHaveBeenCalled());
  vi.mocked(reviewApi.list).mockResolvedValue({reviews:[row({id:'rvw_new',title:'새 검토 요청'}) as any]});
  emitReviewEvent({seq:1,type:'auto_assignment_deferred',request_id:'req_new',payload:{review_id:'rvw_new'}});
  expect(await screen.findByText('새 검토 요청')).toBeInTheDocument();
 });
 it('titles each list row with the masked request title, id chip as the secondary line',async()=>{
  vi.mocked(reviewApi.list).mockResolvedValue({reviews:[row({title:'회의실 예약 자동화'}) as any,row({id:'rvw_2',request_id:'req_2',title:''}) as any]});
  const {container}=renderAt();await screen.findByText('회의실 예약 자동화');
  const titles=[...container.querySelectorAll('.review-row-title')].map(e=>e.textContent);
  expect(titles).toEqual(['회의실 예약 자동화','제목 없는 요청']);
  expect(container.querySelector('.review-row-sub')?.textContent).toContain('req_1');
 });
 it('says honestly when the reviewer may not read the raw text, and shows the masked title',async()=>{
  vi.mocked(requestApi.detail).mockResolvedValue({revisions:[{id:'rev_1'}]} as any);
  vi.mocked(reviewApi.detail).mockResolvedValue({...detail(),request:{title:'마스킹된 제목'}} as any);
  renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));
  expect(await screen.findByText(/원문 열람 권한이 없습니다/)).toBeTruthy();
  expect(screen.getAllByText('마스킹된 제목').length).toBeGreaterThan(0);
  expect(screen.queryByText('요청 원문을 불러오지 못했습니다.')).toBeNull();
 });
 it('still opens the review when the request detail itself is not readable',async()=>{
  vi.mocked(requestApi.detail).mockRejectedValue({status:404,message:'Request not found'});
  vi.mocked(reviewApi.detail).mockResolvedValue({...detail(),request:{title:'요청'}} as any);
  renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));
  expect(await screen.findByLabelText('AI 필요성 수정')).toBeTruthy();
  expect(screen.getByText(/원문 열람 권한이 없습니다/)).toBeTruthy();
 });
 it('shows the raw text when the reviewer may read it',async()=>{
  renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));
  expect(await screen.findByText('원문 내용')).toBeTruthy();
  expect(screen.queryByText(/원문 열람 권한이 없습니다/)).toBeNull();
 });
});
describe('review comparison',()=>{
 it('lists each task once from the current draft and separates the AI original (P6-01)',async()=>{
  const t=(v:number,lead:string)=>({id:`d${v}`,draft_task_id:'draft-1',draft_version:v,title:'화면 개발',method:'일반 기술',lead_org:lead,collab_orgs:[],predecessors:[],deliverable:'결과'});
  const d1={draft_version:1,source:'ai',created_by:'ai',tasks:[t(1,'IT팀')]},d2={draft_version:2,source:'reviewer',created_by:'reviewer',tasks:[t(2,'현업')]};
  vi.mocked(reviewApi.detail).mockResolvedValue({...detail({status:'approved',draft_version:2}),drafts:[d1,d2],original_draft:d1,current_draft:d2} as any);
  const {container}=renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));await screen.findByText('요청');
  expect(container.querySelectorAll('.review-task')).toHaveLength(1);
  expect(screen.getByRole('heading',{name:/업무 분담 \(v2 검토자 수정안\)/})).toBeTruthy();
  expect(container.querySelector('.review-task > small')?.textContent).toContain('AI 원안: IT팀');
  expect(container.querySelectorAll('[data-draft-version]')).toHaveLength(2);
 });
 it('renders the preserved AI original alongside the reviewer value',async()=>{renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));await screen.findByText('요청');expect(screen.getByText('원안: 정보 부족')).toBeTruthy();expect(screen.getByLabelText('AI 필요성 수정')).toHaveProperty('value','정보 부족')});
 it('keeps the 409 conflict notice after reloading the latest review (P3-07)',async()=>{
  renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));await screen.findByText('요청');
  vi.mocked(reviewApi.decide).mockRejectedValue({status:409,code:'HTTP_409',message:'revision conflict'});
  vi.mocked(reviewApi.detail).mockResolvedValue(detail({status:'approved',review_version:3}) as any);
  fireEvent.change(screen.getByLabelText('결정 사유'),{target:{value:'반려 사유'}});fireEvent.click(screen.getByRole('button',{name:'반려'}));
  await waitFor(()=>expect(reviewApi.detail).toHaveBeenCalledTimes(2));
  expect((await screen.findByRole('status')).textContent).toContain('다른 검토자가 먼저 변경했습니다');
  await waitFor(()=>expect(screen.getByRole('button',{name:'반려'})).toBeDisabled());
  expect(screen.getByRole('button',{name:'승인'})).toBeDisabled();expect(screen.getByRole('note').textContent).toContain('이미 처리된 검토');
  expect(screen.getByRole('status').textContent).toContain('다른 검토자가 먼저 변경했습니다');
 });
 it('opens the review of ?request_id= directly (P3-10), also when it is no longer pending',async()=>{
  vi.mocked(reviewApi.list).mockImplementation(async(status='pending')=>({reviews:status==='approved'?[row({status:'approved'}) as any]:[]}));
  vi.mocked(reviewApi.detail).mockResolvedValue(detail({status:'approved'}) as any);
  renderAt('/review?request_id=req_1');
  await screen.findByText('원안: 정보 부족');expect(reviewApi.detail).toHaveBeenCalledWith('rvw_1');
  expect(screen.getByRole('button',{name:'승인'})).toBeDisabled();
 });
 it('opens ?review_id= directly and reports an unknown request_id',async()=>{
  renderAt('/review?review_id=rvw_1');await screen.findByText('원안: 정보 부족');cleanup();
  renderAt('/review?request_id=req_missing');expect((await screen.findByRole('alert')).textContent).toContain('연결된 검토가 없습니다');
 });
 it('sends a decision once even when the button is activated twice in a row',async()=>{
  renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));await screen.findByText('요청');
  let release:(v:unknown)=>void=()=>undefined;vi.mocked(reviewApi.decide).mockReturnValue(new Promise(r=>{release=r}) as any);
  const approve=screen.getByRole('button',{name:/^승인$/});fireEvent.click(approve);fireEvent.click(approve);
  expect(reviewApi.decide).toHaveBeenCalledTimes(1);release({});await screen.findByText(/결정을 저장했습니다/);
 });
});
describe('review evidence viewer',()=>{
 it('opens the cited unit in the source viewer using the attachment named by the run judgment',async()=>{
  vi.mocked(reviewApi.detail).mockResolvedValue({...detail(),outputs:[{id:'o1',question_id:'ai_need',type:'Choice',value:'필요',evidence:[{id:'esp_7',location:{paragraph:3}}]}]} as any);
  vi.mocked(requestApi.evidence).mockResolvedValue({id:'esp_7',attachment_id:'att_2'} as any);
  vi.mocked(requestApi.document).mockResolvedValue({request_id:'req_1',revision:1,revision_id:'rev_1',source:'att_2',kind:'docx',filename:'b.docx',can_read_source:false,units:[{unit_id:'esp_6',order:0,location:{paragraph:2},char_start:0,char_end:1},{unit_id:'esp_7',order:1,location:{paragraph:3},char_start:1,char_end:2}]} as any);
  Element.prototype.scrollTo=vi.fn() as any;
  renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));await screen.findByText('요청');
  fireEvent.click(screen.getByRole('button',{name:'원문 열기'}));
  expect(await screen.findByText(/원문 열람 권한 없음/)).toBeInTheDocument();
  expect(requestApi.evidence).toHaveBeenCalledWith('req_1','esp_7');
  expect(requestApi.document).toHaveBeenCalledWith('req_1','rev_1','att_2');
  expect(document.querySelector('[data-unit-id="esp_7"]')).toHaveAttribute('aria-current','location');
  expect(screen.getAllByText('원문 비공개').length).toBe(2);
 });
});
describe('review detail error ownership (P4-03)',()=>{
 it('keeps the detail error when the list refresh finishes afterwards',async()=>{
  let release:(v:unknown)=>void=()=>undefined;
  vi.mocked(reviewApi.list).mockReturnValue(new Promise(r=>{release=r}) as any);
  vi.mocked(reviewApi.detail).mockRejectedValue({status:404,code:'HTTP_404',message:'Review not found'});
  renderAt('/review?review_id=rvw_x');
  await waitFor(()=>expect(reviewApi.detail).toHaveBeenCalled());
  await screen.findByText(/검토를 찾을 수 없습니다|Review not found/);
  release({reviews:[]});
  await waitFor(()=>expect(screen.getByText(/대기 0건/)).toBeTruthy());
  expect(screen.getByRole('alert').textContent).toMatch(/검토를 찾을 수 없습니다|Review not found/);
 });
 it('shows Korean question and reason labels instead of internal codes (P4-05)',async()=>{
  vi.mocked(reviewApi.detail).mockResolvedValue({...detail(),outputs:[{id:'o1',question_id:'ai_need',type:'Choice',value:'필요',confidence:0.8,evidence:[]}]} as any);
  renderAt('/review?review_id=rvw_1');await screen.findByText('원안: 정보 부족');
  expect(screen.getByText(/AI 필요성 · 선택형/)).toBeTruthy();
  expect(screen.queryByText(/ai_need · Choice/)).toBeNull();
 });
});
it('translates comma-joined reason summaries in the review list (P4-05)',async()=>{
 vi.mocked(reviewApi.list).mockImplementation(async()=>({reviews:[row({reasons_summary:'개발 가능성 미충족, Choice confidence 미충족: ai_need, 미정 분류: lead_org'}) as any]}));
 renderAt();const item=await screen.findByRole('button',{name:/req_1/});
 expect(item.textContent).toContain('선택 확신도 미충족: AI 필요성');expect(item.textContent).toContain('분류 미확정: 담당 조직 · 주관');expect(item.textContent).not.toMatch(/ai_need|lead_org/);
});
describe('review list controls',()=>{
 it('shows an empty-state card with guidance and switches status through the shared select',async()=>{
  vi.mocked(reviewApi.list).mockResolvedValue({reviews:[]} as any);
  renderAt();
  expect(await screen.findByText('대기 중인 검토가 없습니다')).toBeTruthy();
  expect(screen.getByText(/긴급도·사유·대기 시간/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText('검토 상태 필터'),{target:{value:'approved'}});
  await waitFor(()=>expect(reviewApi.list).toHaveBeenLastCalledWith('approved'));
  expect(await screen.findByText('승인 상태의 검토가 없습니다')).toBeTruthy();
  expect(screen.getByRole('checkbox',{name:'긴급 우선 정렬'})).toBeTruthy();
 });
 it('says why the reason-gated decisions are disabled',async()=>{
  renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));await screen.findByText('요청');
  expect(screen.getByRole('button',{name:'반려'})).toBeDisabled();
  expect(screen.getByText(/결정 사유를 입력해야 합니다/)).toBeTruthy();
 });
});

describe('review list row title (TOSS-SCREENS)',()=>{
 const long='req_1b6d959edffd4e4e807ea8bc08bc8acd';
 it('does not put the raw request id in the title slot; a short id chip carries it and the full id stays reachable',async()=>{
  vi.mocked(reviewApi.list).mockImplementation(async()=>({reviews:[row({request_id:long,urgency:'일반'}) as any]}));
  const {container}=renderAt();const item=await screen.findByRole('button',{name:new RegExp(long)});
  expect(container.querySelector('.review-row-title')?.textContent).toBe('제목 없는 요청');expect(container.querySelector('.review-urgency')?.textContent).toBe('일반');
  expect(item.querySelector('strong')?.textContent??'').not.toContain(long);
  const chip=item.querySelector('.short-id');expect(chip?.querySelector('[aria-hidden]')?.textContent).toBe('req_…bc8acd');expect(chip?.getAttribute('title')).toBe(long);
 });
});

it('shows the stored title in the review queue and a masked summary in detail when source access is denied',async()=>{
 const title='회의실 예약 자동화';
 vi.mocked(reviewApi.list).mockResolvedValue({reviews:[row({title,preview:'회의실 예약 자동화를 요청합니다. 상세…'}) as any]} as any);
 vi.mocked(reviewApi.detail).mockResolvedValue({...detail(),request:{title,preview:'회의실 예약 자동화를 요청합니다. 상세…'}} as any);
 vi.mocked(requestApi.detail).mockRejectedValue({status:404,code:'HTTP_404',message:'Request not found'});
 renderAt();
 const item=await screen.findByRole('button',{name:/회의실 예약 자동화/});
 fireEvent.click(item);
 expect(await screen.findByRole('heading',{name:title})).toBeInTheDocument();
 expect(screen.getByText('회의실 예약 자동화를 요청합니다. 상세…')).toBeInTheDocument();
 expect(screen.getByText(/원문 열람 권한이 없습니다/)).toBeInTheDocument();
});

describe('undetermined draft repair (P1-01)',()=>{
 const task={id:'d1',draft_task_id:'draft-1',title:'',method:'미정',lead_org:'미정',collab_orgs:[],predecessors:[],deliverable:''};
 beforeEach(()=>vi.mocked(reviewApi.detail).mockResolvedValue({...detail(),drafts:[{draft_version:1,tasks:[task]}]} as any));
 it('edits all required draft fields and submits the repaired task',async()=>{
  renderAt('/review?review_id=rvw_1');
  fireEvent.change(await screen.findByLabelText('업무 방식'),{target:{value:'일반 기술'}});
  fireEvent.change(screen.getByLabelText('주관 조직'),{target:{value:'IT팀'}});
  fireEvent.change(screen.getByLabelText('업무 제목'),{target:{value:'검토 업무'}});
  fireEvent.change(screen.getByLabelText('산출물'),{target:{value:'검토 결과'}});
  fireEvent.change(screen.getByLabelText('결정 사유'),{target:{value:'미정 필드 보완'}});
  fireEvent.click(screen.getByRole('button',{name:/^수정 승인$/}));
  await waitFor(()=>expect(reviewApi.decide).toHaveBeenCalled());
  expect(vi.mocked(reviewApi.decide).mock.calls[0][1].changes).toMatchObject({draft_tasks:[{draft_task_id:'draft-1',method:'일반 기술',lead_org:'IT팀',title:'검토 업무',deliverable:'검토 결과'}]});
 });
 it('places server validation guidance at the unresolved field',async()=>{
  vi.mocked(reviewApi.decide).mockRejectedValue({status:422,message:'업무 초안의 필드를 확인해 주세요',details:{field_errors:[{draft_task_id:'draft-1',field:'method',message:'업무 방식을 선택해 주세요.'}]}});
  renderAt('/review?review_id=rvw_1');await screen.findByText('원안: 정보 부족');
  fireEvent.click(screen.getByRole('button',{name:/^승인$/}));
  expect(await screen.findByText('업무 방식을 선택해 주세요.')).toBeTruthy();
  expect(screen.getByLabelText('업무 방식')).toHaveAttribute('aria-invalid','true');
 });
});

it('shows classification rule badge and source citations with original text from the permission-checked API', async () => {
 const effect={rule_version:'R-LEAD_ORG-03@1',target:'lead_org',source:'rule:R-LEAD_ORG-03@v1',effect:'rule',outcome:'used',before:'AI팀',after:'IT팀',matches:[{unit_id:'esp_vpn',char_start:0,char_end:3,keyword:'VPN'}]};
 vi.mocked(reviewApi.detail).mockResolvedValue({...detail(),judgment:{lead_org:'IT팀',rule_effects:[effect]}} as any);
 vi.mocked(requestApi.evidence).mockResolvedValue({id:'esp_vpn',attachment_id:'att_vpn',location:{},source_text:'VPN 접속 원문'});
 vi.mocked(requestApi.document).mockResolvedValue({request_id:'req_1',revision:1,revision_id:'rev_1',source:'att_vpn',kind:'md',filename:'vpn.md',can_read_source:true,units:[{unit_id:'esp_vpn',order:0,location:{},char_start:0,char_end:3,text:'VPN 접속 원문'}]});
 Element.prototype.scrollTo=vi.fn();
 renderAt('/review?review_id=rvw_1');
 expect(await screen.findByText('규칙 적용 · R-LEAD_ORG-03 v1')).toBeInTheDocument();
 expect(screen.getByText('모델 판단 AI팀 → 규칙 IT팀')).toBeInTheDocument();
 expect(await screen.findByText('VPN 접속 원문')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'규칙 원문 열기'}));
 await screen.findByText(/원문 ·|규칙 근거 · VPN · 근거 원문/);
 expect(requestApi.document).toHaveBeenCalledWith('req_1','rev_1','att_vpn');
});
