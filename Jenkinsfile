library(
  identifier: 'micro-lib@main',
  retriever: modernSCM([
    $class: 'GitSCMSource',
    remote: 'https://github.com/ThanhMiracle/jenkins-shared-lib.git',
    credentialsId: 'github-pat'
  ])
)

microshopCi(
  dockerCredsId: 'dockerhub-creds',
  composeFiles: ['docker-compose.yml', 'docker-compose.ci.yml'],
  testBranch: 'dev',
  pushBranch: 'main',
  deployBranch: 'main',
  infraServices: ['postgres', 'rabbit', 'mailhog'],
  testServices: ['auth-tests', 'product-tests', 'order-tests', 'payment-tests', 'notify-tests']
),