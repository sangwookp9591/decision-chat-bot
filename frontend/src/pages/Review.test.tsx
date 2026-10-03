import '@testing-library/jest-dom/vitest';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {Review} from './Review';
import {reviewApi} from '../api/reviews';
const row=(over:Record<string,unknown>={})=>({id:'rvw_1',request_id:'req_1',run_id:'run_1',revision_id:'rev_1',draft_version:1,review_version:1,status:'pending',reasons:['정보 부족'],...over});
const detail=(over:Record<string,unknown>={})=>({review:row(over),request:{title:'요청'},judgment:{ai_need:'정보 부족'},outputs:[],drafts:[],history:[],final_classifications:{ai_need:'정보 부족'},final_draft_version:1});
vi.mock('../api/reviews',()=>({reviewApi:{list:vi.fn(),detail:vi.fn(),decide:vi.fn()}}));
vi.mock('../api/requests',()=>({requestApi:{detail:vi.fn().mockResolvedValue({revisions:[{id:'rev_1',text:'원문 내용'}]})}}));
const renderAt=(url='/review')=>render(<MemoryRouter initialEntries={[url]}><Review/></MemoryRouter>);
beforeEach(()=>{cleanup();vi.clearAllMocks();vi.mocked(reviewApi.list).mockImplementation(async(status='pending')=>({reviews:status==='pending'?[row() as any]:[]}));vi.mocked(reviewApi.detail).mockResolvedValue(detail() as any)});
describe('review comparison',()=>{
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
