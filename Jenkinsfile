library(
  identifier: 'micro-lib@main',
  retriever: scm([
    $class: 'GitSCM',
    userRemoteConfigs: [[
      url: 'https://github.com/ThanhMiracle/jenkins-shared-lib.git',
      credentialsId: 'github-pat'
    ]],
    branches: [[name: '*/main']],
    extensions: [
      [$class: 'CleanBeforeCheckout']  // optional: keeps library checkout clean
    ]
  ])
)

microshopCi(
  dockerCredsId: 'dockerhub-creds',
  composeFiles: ['docker-compose.yml', 'docker-compose.ci.yml'],

  // Optional overrides (keep or remove)
  testBranch: 'dev',
  pushBranch: 'main',
  deployBranch: 'main',

  infraServices: ['postgres', 'rabbit', 'mailhog'],
  testServices: ['auth-tests', 'product-tests', 'order-tests', 'payment-tests', 'notify-tests']
)