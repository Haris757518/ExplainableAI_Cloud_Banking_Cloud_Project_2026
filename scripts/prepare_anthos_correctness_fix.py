"""Prepare a correctness-first patch without modifying the pinned upstream tree."""
import difflib,json,shutil,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'vendor/bank-of-anthos'
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path(r'D:\BankingResearch\Experiments\AnthosCorrectness-v4'));args=parser.parse_args()
TARGET=args.output
PATCH=ROOT/'deploy/correctness-fix'
PATCH.mkdir(exist_ok=True)
if TARGET.exists():raise SystemExit('Preserve the existing validation tree; do not overwrite it.')
TARGET.mkdir(parents=True)
changes=[]

def change(relative,transform):
    old=(SOURCE/relative).read_text()
    new=transform(old)
    if new==old:raise ValueError('Expected source transformation missing: '+relative)
    path=TARGET/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(new)
    changes.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))

for service,controller in [('balancereader','BalanceReaderController'),('transactionhistory','TransactionHistoryController')]:
    base=f'src/ledger/{service}'
    shutil.copytree(SOURCE/base,TARGET/base,ignore=shutil.ignore_patterns('target','.git'))
    package=f'{base}/src/main/java/anthos/samples/bankofanthos/{service}'
    def fix_controller(text,service=service):
        text=text.replace('import java.util.concurrent.ExecutionException;','import org.springframework.dao.DataAccessException;')
        text=text.replace('import com.google.common.util.concurrent.UncheckedExecutionException;\n','')
        text=text.replace('ExecutionException | UncheckedExecutionException','DataAccessException')
        text=text.replace('LOGGER.error("Cache error");','LOGGER.error("Ledger read error");').replace('"cache error",','"ledger read error",')
        if service=='balancereader':
            text=text.replace('this.version = version;','this.version = version;\n        this.localRoutingNum = localRoutingNum;')
            text=text.replace('// Load from cache\n            Long balance = cache.get(accountId);','// Read one committed ledger snapshot; do not depend on cursor order.\n            Long balance = dbRepo.findBalance(accountId, localRoutingNum);')
        else:
            text=text.replace('private String version;','private String version;\n    private String localRoutingNum;')
            text=text.replace('this.version = version;','this.version = version;\n        this.localRoutingNum = localRoutingNum;')
            text=text.replace('// Load from cache\n            Deque<Transaction> historyList = cache.get(accountId);','// Read committed records on every request, including late lower IDs.\n            Collection<Transaction> historyList = dbRepo.findForAccount(\n                accountId, localRoutingNum,\n                org.springframework.data.domain.PageRequest.of(0, historyLimit));')
        return text
    change(package+'/'+controller+'.java',fix_controller)
    repo=package+'/TransactionRepository.java'
    def fix_repo(text,service=service):
        if service=='transactionhistory':return text.replace('ORDER BY t.timestamp DESC")','ORDER BY t.timestamp DESC, t.transactionId DESC")')
        start=text.index('    @Query(value = "SELECT "')
        end=text.index('    Long findBalance',start)
        return text[:start]+'''    @Query(value = "SELECT "
    + "COALESCE(SUM(CASE WHEN TO_ACCT=?1 AND TO_ROUTE=?2 "
    + "THEN CAST(AMOUNT AS BIGINT) ELSE 0 END),0) - "
    + "COALESCE(SUM(CASE WHEN FROM_ACCT=?1 AND FROM_ROUTE=?2 "
    + "THEN CAST(AMOUNT AS BIGINT) ELSE 0 END),0) FROM TRANSACTIONS",
        nativeQuery = true)
'''+text[end:]
    change(repo,fix_repo)
    pom=base+'/pom.xml'
    def add_test_database(text):
        boundary=text.index('</dependencyManagement>')+len('</dependencyManagement>')
        return text[:boundary]+text[boundary:].replace('    <dependencies>\n','    <dependencies>\n        <dependency><groupId>com.h2database</groupId><artifactId>h2</artifactId><scope>test</scope></dependency>\n        <dependency><groupId>org.springframework</groupId><artifactId>spring-test</artifactId><scope>test</scope></dependency>\n',1)
    change(pom,add_test_database)
    test=f'{base}/src/test/java/anthos/samples/bankofanthos/{service}/{controller}Test.java'
    def fix_tests(text,service=service,controller=controller):
        variable=controller[0].lower()+controller[1:]
        text=text.replace('private JWTVerifier verifier;','private JWTVerifier verifier;\n    @Mock\n    private TransactionRepository dbRepo;')
        text=text.replace('        when(verifier.verify(TOKEN)).thenReturn(jwt);',f'        org.springframework.test.util.ReflectionTestUtils.setField({variable}, "dbRepo", dbRepo);\n        when(verifier.verify(TOKEN)).thenReturn(jwt);',1)
        if service=='balancereader':
            text=text.replace('when(cache.get(AUTHED_ACCOUNT_NUM)).thenReturn(BALANCE);','when(dbRepo.findBalance(AUTHED_ACCOUNT_NUM, LOCAL_ROUTING_NUM)).thenReturn(BALANCE);')
            text=text.replace('when(cache.get(AUTHED_ACCOUNT_NUM)).thenThrow(ExecutionException.class);','when(dbRepo.findBalance(AUTHED_ACCOUNT_NUM, LOCAL_ROUTING_NUM)).thenThrow(org.springframework.dao.DataAccessResourceFailureException.class);')
        else:
            text=text.replace('        when(cache.stats()).thenReturn(stats);','        when(cache.stats()).thenReturn(stats);')
            needle=f'        org.springframework.test.util.ReflectionTestUtils.setField({variable}, "dbRepo", dbRepo);'
            text=text.replace(needle,needle+f'\n        org.springframework.test.util.ReflectionTestUtils.setField({variable}, "historyLimit", 100);')
            text=text.replace('when(cache.get(AUTHED_ACCOUNT_NUM)).thenReturn(transactions);','when(dbRepo.findForAccount(org.mockito.ArgumentMatchers.eq(AUTHED_ACCOUNT_NUM), org.mockito.ArgumentMatchers.eq(LOCAL_ROUTING_NUM), org.mockito.ArgumentMatchers.any())).thenReturn(new java.util.LinkedList<>());')
            text=text.replace('when(cache.get(AUTHED_ACCOUNT_NUM)).thenThrow(ExecutionException.class);','when(dbRepo.findForAccount(org.mockito.ArgumentMatchers.eq(AUTHED_ACCOUNT_NUM), org.mockito.ArgumentMatchers.eq(LOCAL_ROUTING_NUM), org.mockito.ArgumentMatchers.any())).thenThrow(org.springframework.dao.DataAccessResourceFailureException.class);')
        return text.replace('cache throws an error','ledger query throws an error')
    change(test,fix_tests)
    body = '''assertEquals(9964L, repo.findBalance("sender", "123"));
        assertEquals(36L, repo.findBalance("recipient", "123"));
        assertEquals(0L, repo.findBalance("empty", "123"));
        assertEquals(0L, repo.findBalance("sender", "wrong-route"));''' if service=='balancereader' else '''var sender = repo.findForAccount("sender", "123", org.springframework.data.domain.PageRequest.of(0, 100));
        var recipient = repo.findForAccount("recipient", "123", org.springframework.data.domain.PageRequest.of(0, 100));
        assertEquals(3, sender.size());
        assertEquals(2, recipient.size());
        assertEquals(3L, sender.stream().map(Transaction::getTransactionId).distinct().count());
        assertTrue(recipient.stream().anyMatch(t -> t.getTransactionId() == 2L));
        assertEquals(1, repo.findForAccount("sender", "123", org.springframework.data.domain.PageRequest.of(0, 1)).size());
        assertTrue(repo.findForAccount("sender", "wrong-route", org.springframework.data.domain.PageRequest.of(0, 100)).isEmpty());'''
    integration=(PATCH/'CommitOrderRegressionTest.java.template').read_text().replace('SERVICE',service).replace('VERIFY_BODY',body)
    target=TARGET/f'{base}/src/test/java/anthos/samples/bankofanthos/{service}/CommitOrderRegressionTest.java'
    target.write_text(integration)
    rel=str(target.relative_to(TARGET)).replace('\\','/')
    changes.append(''.join(difflib.unified_diff([],integration.splitlines(True),fromfile='/dev/null',tofile='b/'+rel)))
patch=PATCH/'anthos-authoritative-reads.patch';patch.write_text(''.join(changes))
(PATCH/'patch-manifest.json').write_text(json.dumps({'upstream_revision':'db35fea9fd090150e2398106aadb475576f80d94','patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'validation_tree':str(TARGET),'policy':'Correctness-first committed ledger reads; additional database work requires performance validation. No AWS deployment performed.'},indent=2))
print(TARGET)
