import '@testing-library/jest-dom/vitest';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {Review} from './Review';
import {reviewApi} from '../api/reviews';
import {requestApi} from '../api/requests';
const row=(over:Record<string,unknown>={})=>({id:'rvw_1',request_id:'req_1',run_id:'run_1',revision_id:'rev_1',draft_version:1,review_version:1,status:'pending',reasons:['정보 부족'],...over});
const detail=(over:Record<string,unknown>={})=>({review:row(over),request:{title:'요청'},judgment:{ai_need:'정보 부족'},outputs:[],drafts:[],history:[],final_classifications:{ai_need:'정보 부족'},final_draft_version:1});
vi.mock('../api/reviews',()=>({reviewApi:{list:vi.fn(),detail:vi.fn(),decide:vi.fn()}}));
vi.mock('../api/requests',()=>({requestApi:{detail:vi.fn().mockResolvedValue({revisions:[{id:'rev_1',text:'원문 내용'}]}),judgment:vi.fn(),document:vi.fn()}}));
const renderAt=(url='/review')=>render(<MemoryRouter initialEntries={[url]}><Review/></MemoryRouter>);
beforeEach(()=>{cleanup();vi.clearAllMocks();vi.mocked(reviewApi.list).mockImplementation(async(status='pending')=>({reviews:status==='pending'?[row() as any]:[]}));vi.mocked(reviewApi.detail).mockResolvedValue(detail() as any)});
describe('review comparison',()=>{
 it('lists each task once from the current draft and separates the AI original (P6-01)',async()=>{
  const t=(v:number,lead:string)=>({id:`d${v}`,draft_task_id:'draft-1',draft_version:v,title:'화면 개발',method:'일반 기술',lead_org:lead,collab_orgs:[],predecessors:[],deliverable:'결과'});
  const d1={draft_version:1,source:'ai',created_by:'ai',tasks:[t(1,'IT팀')]},d2={draft_version:2,source:'reviewer',created_by:'reviewer',tasks:[t(2,'현업')]};
  vi.mocked(reviewApi.detail).mockResolvedValue({...detail({status:'approved',draft_version:2}),drafts:[d1,d2],original_draft:d1,current_draft:d2} as any);
  const {container}=renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));await screen.findByText('요청');
  expect(container.querySelectorAll('.review-task')).toHaveLength(1);
  expect(screen.getByRole('heading',{name:/업무 분담 \(v2 검토자 수정안\)/})).toBeTruthy();
  expect(container.querySelector('.review-task small')?.textContent).toContain('AI 원안: IT팀');
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
  vi.mocked(requestApi.judgment).mockResolvedValue({outputs:[{evidence:[{id:'esp_7',attachment_id:'att_2'}]}]} as any);
  vi.mocked(requestApi.document).mockResolvedValue({request_id:'req_1',revision:1,revision_id:'rev_1',source:'att_2',kind:'docx',filename:'b.docx',can_read_source:false,units:[{unit_id:'esp_6',order:0,location:{paragraph:2},char_start:0,char_end:1},{unit_id:'esp_7',order:1,location:{paragraph:3},char_start:1,char_end:2}]} as any);
  Element.prototype.scrollTo=vi.fn() as any;
  renderAt();fireEvent.click(await screen.findByRole('button',{name:/req_1/}));await screen.findByText('요청');
  fireEvent.click(screen.getByRole('button',{name:'원문 열기'}));
  expect(await screen.findByText(/원문 열람 권한 없음/)).toBeInTheDocument();
  expect(requestApi.judgment).toHaveBeenCalledWith('req_1','run_1');
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

